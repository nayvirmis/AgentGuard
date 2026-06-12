from backend.app.db import normalize_database_url


def test_normalize_database_url_uses_psycopg3() -> None:
    assert (
        normalize_database_url("postgres://user:pass@host/db")
        == "postgresql+psycopg://user:pass@host/db"
    )
    assert (
        normalize_database_url("postgresql://user:pass@host/db")
        == "postgresql+psycopg://user:pass@host/db"
    )
    assert normalize_database_url("sqlite:///agentguard.db") == "sqlite:///agentguard.db"
