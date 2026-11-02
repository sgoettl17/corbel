"""Runtime configuration read from environment variables (set by the plugin's userConfig)."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

ENVIRONMENTS = {
    "production": ("https://api.procore.com", "https://login.procore.com"),
    "sandbox": ("https://sandbox.procore.com", "https://login-sandbox.procore.com"),
}


@dataclass(frozen=True)
class Config:
    client_id: str = ""
    client_secret: str = ""
    access_token: str = ""
    company_id: str = ""
    environment: str = "production"
    allow_writes: bool = False

    @property
    def api_base(self) -> str:
        return ENVIRONMENTS[self.environment][0]

    @property
    def login_base(self) -> str:
        return ENVIRONMENTS[self.environment][1]

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> Config:
        env = os.environ if env is None else env
        environment = (env.get("CORBEL_ENVIRONMENT") or "production").strip().lower()
        if environment not in ENVIRONMENTS:
            raise ValueError(f"CORBEL_ENVIRONMENT must be one of {sorted(ENVIRONMENTS)}")
        return cls(
            client_id=env.get("CORBEL_CLIENT_ID", "").strip(),
            client_secret=env.get("CORBEL_CLIENT_SECRET", "").strip(),
            access_token=env.get("CORBEL_ACCESS_TOKEN", "").strip(),
            company_id=env.get("CORBEL_COMPANY_ID", "").strip(),
            environment=environment,
            allow_writes=env.get("CORBEL_ALLOW_WRITES", "").strip().lower() in {"1", "true", "yes"},
        )
