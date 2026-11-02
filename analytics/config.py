"""Environment-based configuration with fail-fast validation.

No credential is ever hard-coded or logged. The real .env file is ignored by
git; .env.example contains placeholders only.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.engine import URL

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


class ConfigurationError(RuntimeError):
    """Raised when required database configuration is absent or invalid."""


@dataclass(frozen=True)
class Settings:
    mysql_host: str
    mysql_port: int
    mysql_database: str
    mysql_user: str
    mysql_password: str
    mysql_test_database: str
    mysql_admin_user: str | None
    mysql_admin_password: str | None

    @property
    def database_url(self) -> URL:
        return URL.create(
            drivername="mysql+pymysql",
            username=self.mysql_user,
            password=self.mysql_password,
            host=self.mysql_host,
            port=self.mysql_port,
            database=self.mysql_database,
            query={"charset": "utf8mb4"},
        )

    @property
    def test_database_url(self) -> URL:
        return URL.create(
            drivername="mysql+pymysql",
            username=self.mysql_user,
            password=self.mysql_password,
            host=self.mysql_host,
            port=self.mysql_port,
            database=self.mysql_test_database,
            query={"charset": "utf8mb4"},
        )

    def safe_description(self) -> str:
        return (
            f"MySQL {self.mysql_user}@{self.mysql_host}:{self.mysql_port}"
            f"/{self.mysql_database} (password hidden)"
        )


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ConfigurationError(
            f"Missing required environment variable {name}. "
            "Copy .env.example to .env and fill in the values."
        )
    return value


def get_settings() -> Settings:
    """Load and validate settings. Called by database-facing scripts/tests."""
    host = os.getenv("MYSQL_HOST", "127.0.0.1").strip() or "127.0.0.1"
    port_raw = os.getenv("MYSQL_PORT", "3306").strip() or "3306"
    try:
        port = int(port_raw)
    except ValueError as exc:
        raise ConfigurationError(f"MYSQL_PORT must be an integer, got {port_raw!r}") from exc
    if not 1 <= port <= 65535:
        raise ConfigurationError("MYSQL_PORT must be between 1 and 65535")

    database = _required("MYSQL_DATABASE")
    user = _required("MYSQL_USER")
    password = os.getenv("MYSQL_PASSWORD", "")
    if not password:
        raise ConfigurationError(
            "MYSQL_PASSWORD is empty. Set it in .env (never commit the real .env)."
        )

    test_database = os.getenv("MYSQL_TEST_DATABASE", f"{database}_test").strip()
    if test_database == database:
        raise ConfigurationError("MYSQL_TEST_DATABASE must differ from MYSQL_DATABASE")

    return Settings(
        mysql_host=host,
        mysql_port=port,
        mysql_database=database,
        mysql_user=user,
        mysql_password=password,
        mysql_test_database=test_database,
        mysql_admin_user=os.getenv("MYSQL_ADMIN_USER") or None,
        mysql_admin_password=os.getenv("MYSQL_ADMIN_PASSWORD") or None,
    )
