from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Fitness Tracking Management System API"
    app_env: str = "development"
    database_url: str = Field(alias="DATABASE_URL")
    cors_origins: str = Field(default="http://localhost:5173", alias="CORS_ORIGINS")
    frontend_url: str = Field(default="http://localhost:5173", alias="FRONTEND_URL")
    frontend_dist_dir: str | None = Field(default=None, alias="FRONTEND_DIST_DIR")
    secret_key: str = Field(default="dev-only-change-me", alias="SECRET_KEY")
    admin_bootstrap_username: str = Field(default="admin", alias="ADMIN_BOOTSTRAP_USERNAME")
    admin_bootstrap_password: str | None = Field(default=None, alias="ADMIN_BOOTSTRAP_PASSWORD")
    exercisedb_api_url: str = Field(
        default="https://oss.exercisedb.dev/api/v1/exercises", alias="EXERCISEDB_API_URL"
    )
    exercisedb_sync_on_seed: bool = Field(default=False, alias="EXERCISEDB_SYNC_ON_SEED")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4.1-mini", alias="OPENAI_MODEL")
    llm_force_failure: bool = Field(default=False, alias="LLM_FORCE_FAILURE")
    llm_timeout_seconds: int = Field(default=25, alias="LLM_TIMEOUT_SECONDS")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def sqlalchemy_database_url(self) -> str:
        """Use psycopg 3 when a cloud vendor returns a plain Postgres URL."""
        if self.database_url.startswith("postgresql://"):
            return self.database_url.replace("postgresql://", "postgresql+psycopg://", 1)
        if self.database_url.startswith("postgres://"):
            return self.database_url.replace("postgres://", "postgresql+psycopg://", 1)
        return self.database_url


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
