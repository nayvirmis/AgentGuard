import sys
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(ROOT / ".env", ROOT / ".env.local"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "AgentGuard"
    app_env: str = "development"
    auth_mode: str = "development"
    demo_user_id: str = "demo-user"
    database_url: str = f"sqlite:///{ROOT / 'agentguard.db'}"
    frontend_origin: str = "http://localhost:3000"
    llm_provider: str = "fake"
    openai_api_key: str | None = None
    openai_model: str = "gpt-5.5"
    clerk_jwks_url: str | None = None
    clerk_issuer: str | None = None
    daily_run_quota: int = 25
    max_tool_calls: int = 6
    max_output_chars: int = 12_000
    approval_ttl_minutes: int = 30
    mcp_server_command: str = sys.executable
    mcp_server_args: str = "-m,mcp_server.server"
    private_identifiers: list[str] = Field(default_factory=list)

    @property
    def mcp_args(self) -> list[str]:
        return [value for value in self.mcp_server_args.split(",") if value]


@lru_cache
def get_settings() -> Settings:
    return Settings()
