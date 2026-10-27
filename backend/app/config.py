"""Application settings.

Every value is read from environment variables or the ``backend/.env`` file
(NFR-MNT-005, NFR-SEC-002). Secrets have no default in code: the API refuses to
start until DATABASE_URL and SECRET_KEY are set, so nothing sensitive is ever
hard-coded.
"""
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    # ---- App ---------------------------------------------------------------
    app_name: str = "FixFlow"
    app_env: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"
    api_prefix: str = "/api"
    cors_origins: str = "http://localhost:5173"
    max_request_bytes: int = Field(default=1_000_000, ge=10_000)  # IR-012

    # ---- Database (required) ----------------------------------------------
    database_url: str
    db_pool_size: int = Field(default=5, ge=1)
    db_max_overflow: int = Field(default=10, ge=0)
    db_echo: bool = False

    # ---- Tokens (SECRET_KEY required) -------------------------------------
    secret_key: str = Field(min_length=32)
    jwt_algorithm: Literal["HS256", "HS384", "HS512"] = "HS256"
    access_token_expire_minutes: int = Field(default=480, ge=5)

    # ---- Passwords: PBKDF2-HMAC-SHA256 with a per-user salt ---------------
    password_hash_iterations: int = Field(default=600_000, ge=1_000)
    password_salt_bytes: int = Field(default=16, ge=16)
    password_pepper: str = ""  # optional server-side secret mixed into every hash
    password_min_length: int = Field(default=8, ge=8)
    login_max_attempts: int = Field(default=5, ge=1)
    login_lockout_minutes: int = Field(default=15, ge=1)

    # ---- Optional AI (Google Gemini) --------------------------------------
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash-lite"
    gemini_api_url: str = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    gemini_timeout_seconds: float = Field(default=40, gt=0)

    # ---- Defaults for each new company -------------------------------------
    default_sla_critical_hours: int = Field(default=24, ge=1)
    default_sla_high_hours: int = Field(default=72, ge=1)
    default_sla_medium_hours: int = Field(default=168, ge=1)
    default_sla_low_hours: int = Field(default=336, ge=1)


    model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8", extra="ignore")

    @field_validator("secret_key")
    @classmethod
    def reject_placeholder_secret(cls, value: str) -> str:
        if value.lower().startswith(("replace", "change", "your-")):
            raise ValueError("SECRET_KEY still holds the example placeholder. Generate a real random value.")
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def ai_configured(self) -> bool:
        return bool(self.gemini_api_key.strip())

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    try:
        return Settings()  # type: ignore[call-arg]
    except ValidationError as exc:
        problems = "\n".join(
            f"  - {'.'.join(str(p) for p in err['loc']).upper() or 'SETTINGS'}: {err['msg']}" for err in exc.errors()
        )
        raise SystemExit(
            f"\nFixFlow configuration error. Fix these values in {ENV_FILE}:\n{problems}\n"
            "Copy backend/.env.example to backend/.env if you have not done so yet.\n"
        ) from None


settings = get_settings()
