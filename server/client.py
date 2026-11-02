"""Procore HTTP client: OAuth client-credentials auth, retries, and rate-limit handling.

All requests go only to the Procore host chosen by configuration; callers supply paths from the
bundled endpoint index, never arbitrary URLs.
"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping
from typing import Any

from config import Config

Transport = Callable[[str, str, Mapping[str, str], bytes | None, float], tuple[int, dict, bytes]]
MAX_RETRIES = 3
TIMEOUT_SECONDS = 30.0


class ProcoreError(Exception):
    """A failed Procore call, with a message safe to show the model (never includes secrets)."""

    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


def urllib_transport(
    method: str, url: str, headers: Mapping[str, str], data: bytes | None, timeout: float
) -> tuple[int, dict, bytes]:
    if not url.startswith("https://"):
        raise ProcoreError("Refusing to call a non-HTTPS URL")
    request = urllib.request.Request(url, data=data, method=method, headers=dict(headers))  # noqa: S310
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            return response.status, dict(response.headers), response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers), exc.read()
    except urllib.error.URLError as exc:
        raise ProcoreError(f"Could not reach Procore: {exc.reason}") from exc


class ProcoreClient:
    def __init__(
        self,
        config: Config,
        transport: Transport = urllib_transport,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.config = config
        self._transport = transport
        self._sleep = sleep
        self._token = ""
        self._token_expires = 0.0

    def _access_token(self) -> str:
        if self.config.access_token:
            return self.config.access_token
        if self._token and time.time() < self._token_expires - 60:
            return self._token
        if not (self.config.client_id and self.config.client_secret):
            raise ProcoreError(
                "Procore credentials are not configured. Set the client ID and client secret "
                "in the plugin settings (or CORBEL_ACCESS_TOKEN)."
            )
        form = urllib.parse.urlencode(
            {
                "grant_type": "client_credentials",
                "client_id": self.config.client_id,
                "client_secret": self.config.client_secret,
            }
        ).encode()
        status, _, raw = self._transport(
            "POST",
            f"{self.config.login_base}/oauth/token",
            {"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
            form,
            TIMEOUT_SECONDS,
        )
        if status != 200:
            raise ProcoreError(
                f"Procore rejected the credentials (HTTP {status}). Check the client ID, "
                "client secret and environment (production or sandbox).",
                status,
            )
        payload = json.loads(raw)
        self._token = payload["access_token"]
        self._token_expires = time.time() + float(payload.get("expires_in", 5400))
        return self._token

    def request(
        self,
        method: str,
        path: str,
        query: list[tuple[str, str]] | None = None,
        body: Any = None,
        company_id: str | None = None,
    ) -> tuple[Any, dict]:
        """Call the API and return (parsed JSON or None, response headers)."""
        url = f"{self.config.api_base}{path}"
        if query:
            url += "?" + urllib.parse.urlencode(query)
        headers = {"Accept": "application/json", "Authorization": f"Bearer {self._access_token()}"}
        company = company_id or self.config.company_id
        if company:
            headers["Procore-Company-Id"] = str(company)
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"

        for attempt in range(MAX_RETRIES + 1):
            status, resp_headers, raw = self._transport(method, url, headers, data, TIMEOUT_SECONDS)
            if status in (429, 502, 503, 504) and attempt < MAX_RETRIES:
                delay = _retry_delay(resp_headers, attempt)
                print(f"corbel: HTTP {status}, retrying in {delay:.1f}s", file=sys.stderr)
                self._sleep(delay)
                continue
            break
        if status >= 400:
            raise ProcoreError(_error_message(status, raw), status)
        parsed = json.loads(raw) if raw.strip() else None
        return parsed, resp_headers


def _retry_delay(headers: Mapping[str, str], attempt: int) -> float:
    lowered = {k.lower(): v for k, v in headers.items()}
    for key in ("retry-after", "x-rate-limit-reset"):
        try:
            return min(max(float(lowered[key]), 0.5), 60.0)
        except (KeyError, ValueError):
            continue
    return float(2**attempt)


def _error_message(status: int, raw: bytes) -> str:
    hint = {
        401: "Unauthorized: the token is invalid or expired.",
        403: "Forbidden: the Procore user or app lacks permission for this resource.",
        404: "Not found: check the IDs and that Procore-Company-Id is correct.",
        422: "Procore rejected the request data.",
        429: "Rate limited by Procore; retries were exhausted. Try again shortly.",
    }.get(status, "Procore returned an error.")
    detail = raw.decode("utf-8", "replace").strip()[:500]
    return f"HTTP {status}. {hint}" + (f" Details: {detail}" if detail else "")
