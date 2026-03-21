"""Application configuration using Pydantic Settings."""
from functools import lru_cache
from typing import List, Optional

from pydantic import AnyHttpUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_name: str = "Conduit"
    app_version: str = "0.1.0"
    environment: str = Field(default="development", pattern="^(development|staging|production)$")
    debug: bool = False
    log_level: str = "INFO"

    # API
    api_prefix: str = "/api/v1"
    allowed_origins: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://conduit:conduit@localhost:5432/conduit"
    )
    db_pool_size: int = 10
    db_max_overflow: int = 20

    # ModMed / FHIR Source
    modmed_base_url: AnyHttpUrl = Field(default="https://api.modmed.com/fhir/r4")
    modmed_token_url: AnyHttpUrl = Field(
        default="https://api.modmed.com/oauth2/token"
    )
    modmed_client_id: str = Field(default="")
    modmed_client_secret: str = Field(default="")
    modmed_scope: str = "fhir.read"
    fhir_page_size: int = 50
    fhir_request_timeout: int = 30

    # Audit
    audit_schema: str = "audit"
    audit_retention_days: int = 2555  # ~7 years (HIPAA requirement)

    # Encryption (KMS key ARN or local secret for dev)
    encryption_key: str = Field(default="dev-only-32-byte-key-replace-me!")

    # Feature flags
    enable_browser_connector: bool = False
    enable_fhir_write_connector: bool = True

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
