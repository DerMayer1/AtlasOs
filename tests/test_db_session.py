"""Database URL normalization for managed-host DSNs."""

import pytest

from atlas.platform.db.session import normalize_database_url


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        # Managed hosts (Render/Railway/Heroku) hand out bare Postgres DSNs.
        ("postgres://u:p@host:5432/atlas", "postgresql+psycopg://u:p@host:5432/atlas"),
        ("postgresql://u:p@host:5432/atlas", "postgresql+psycopg://u:p@host:5432/atlas"),
        # An explicit driver is respected, never rewritten.
        ("postgresql+psycopg://u:p@host/atlas", "postgresql+psycopg://u:p@host/atlas"),
        ("postgresql+asyncpg://u:p@host/atlas", "postgresql+asyncpg://u:p@host/atlas"),
        # SQLite is untouched.
        ("sqlite:///var/atlas.db", "sqlite:///var/atlas.db"),
    ],
)
def test_normalize_database_url_pins_psycopg_for_bare_postgres(given, expected):
    assert normalize_database_url(given) == expected


def test_normalize_database_url_preserves_password_and_query():
    normalized = normalize_database_url("postgres://u:s3cr3t@host:5432/atlas?sslmode=require")
    assert normalized.startswith("postgresql+psycopg://u:s3cr3t@host:5432/atlas")
    assert "sslmode=require" in normalized
