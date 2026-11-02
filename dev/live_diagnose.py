"""Diagnose why a Procore app can't see data. Prints non-secret facts only.

Usage: uv run --env-file .env python dev/live_diagnose.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parent.parent / "server")]

from client import ProcoreClient, ProcoreError, urllib_transport  # noqa: E402
from config import Config  # noqa: E402

SECRET_KEYS = {"access_token", "refresh_token"}


def main() -> int:
    os.environ.setdefault("CORBEL_ENVIRONMENT", "sandbox")
    config = Config.from_env()
    print(f"api_base={config.api_base} login_base={config.login_base}")
    print(f"client_id length={len(config.client_id)} company_id={config.company_id!r}")

    client = ProcoreClient(config)
    try:
        client._access_token()
    except ProcoreError as exc:
        print(f"token FAIL: {exc}")
        return 1
    print("token OK")

    # Token response fields other than the secrets themselves.
    import urllib.parse

    form = urllib.parse.urlencode(
        {
            "grant_type": "client_credentials",
            "client_id": config.client_id,
            "client_secret": config.client_secret,
        }
    ).encode()
    _, _, raw = urllib_transport(
        "POST",
        f"{config.login_base}/oauth/token",
        {"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
        form,
        30.0,
    )
    info = json.loads(raw)
    print("token fields:", {k: v for k, v in info.items() if k not in SECRET_KEYS})

    probes = [
        ("me (no company header)", "/rest/v1.0/me", ""),
        ("companies (no company header)", "/rest/v1.0/companies", ""),
        ("companies (with company header)", "/rest/v1.0/companies", config.company_id),
        (
            "company by id",
            f"/rest/v1.0/companies/{config.company_id}",
            config.company_id,
        ),
    ]
    for label, path, company in probes:
        probe_config = Config(
            client_id=config.client_id,
            client_secret=config.client_secret,
            company_id=company,
            environment=config.environment,
        )
        probe = ProcoreClient(probe_config)
        probe._token, probe._token_expires = client._token, client._token_expires
        try:
            data, _ = probe.request("GET", path)
        except ProcoreError as exc:
            print(f"{label}: {exc}")
            continue
        summary = f"{len(data)} record(s)" if isinstance(data, list) else json.dumps(data)[:300]
        print(f"{label}: OK {summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
