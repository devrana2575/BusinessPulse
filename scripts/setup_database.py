"""Create/apply the BusinessPulse MySQL schema, indexes, seeds and views.

Usage (PowerShell):
    python scripts/setup_database.py --database businesspulse

The explicit --reset option drops the selected database and is destructive.
Provisioned application accounts are restricted to the configured loopback host.

The real .env is required; credentials are never printed.
"""

from __future__ import annotations

import argparse
import ipaddress
import re
import sys
from pathlib import Path
from typing import Iterable

import pymysql

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analytics.config import ConfigurationError, Settings, get_settings  # noqa: E402

DB_DIR = ROOT / "database"
DEFAULT_FILES = ("schema.sql", "indexes.sql", "seed_data.sql", "views.sql")
IDENTIFIER = re.compile(r"^[A-Za-z0-9_]+$")


def split_sql(text: str) -> list[str]:
    """Split MySQL statements while respecting quotes and comments."""
    statements: list[str] = []
    buf: list[str] = []
    in_single = in_double = in_backtick = False
    i = 0
    length = len(text)
    while i < length:
        ch = text[i]
        nxt = text[i + 1] if i + 1 < length else ""
        if not (in_single or in_double or in_backtick):
            if ch == "-" and nxt == "-":
                newline = text.find("\n", i)
                i = length if newline == -1 else newline + 1
                continue
            if ch == "/" and nxt == "*":
                end = text.find("*/", i + 2)
                i = length if end == -1 else end + 2
                continue
            if ch == ";":
                statement = "".join(buf).strip()
                if statement:
                    statements.append(statement)
                buf = []
                i += 1
                continue
        if ch == "\\" and (in_single or in_double) and nxt:
            buf.extend([ch, nxt])
            i += 2
            continue
        if ch == "'" and not in_double and not in_backtick:
            if in_single and nxt == "'":
                buf.extend([ch, nxt])
                i += 2
                continue
            in_single = not in_single
        elif ch == '"' and not in_single and not in_backtick:
            if in_double and nxt == '"':
                buf.extend([ch, nxt])
                i += 2
                continue
            in_double = not in_double
        elif ch == "`" and not in_single and not in_double:
            in_backtick = not in_backtick
        buf.append(ch)
        i += 1
    final = "".join(buf).strip()
    if final:
        statements.append(final)
    return statements


def read_sql(name: str) -> list[str]:
    path = DB_DIR / name
    if not path.exists():
        raise FileNotFoundError(path)
    return split_sql(path.read_text(encoding="utf-8"))


def execute_many(
    connection: pymysql.connections.Connection,
    statements: Iterable[str],
    *,
    tolerate_index_errors: bool = False,
    label: str = "SQL",
) -> tuple[int, list[str]]:
    executed = 0
    errors: list[str] = []
    with connection.cursor() as cursor:
        for statement in statements:
            try:
                cursor.execute(statement)
                executed += 1
            except pymysql.err.OperationalError as exc:
                code = exc.args[0] if exc.args else 0
                # 1061 duplicate key name; 1060 duplicate column; 1826 duplicate FK
                if tolerate_index_errors and code in (1060, 1061, 1826):
                    continue
                errors.append(f"{label}: {code}: {str(exc)[:300]}")
            except pymysql.MySQLError as exc:
                code = exc.args[0] if exc.args else 0
                errors.append(f"{label}: {code}: {str(exc)[:300]}")
    connection.commit()
    return executed, errors


def admin_connection(settings: Settings, *, with_database: bool = False):
    if not settings.mysql_admin_user:
        raise ConfigurationError(
            "MYSQL_ADMIN_USER is not set. Set it in .env to create/reset a database, "
            "or create the database and user manually (see README)."
        )
    return pymysql.connect(
        host=settings.mysql_host,
        port=settings.mysql_port,
        user=settings.mysql_admin_user,
        password=settings.mysql_admin_password or "",
        database=settings.mysql_database if with_database else None,
        charset="utf8mb4",
        autocommit=True,
    )


def app_connection(settings: Settings, database: str):
    return pymysql.connect(
        host=settings.mysql_host,
        port=settings.mysql_port,
        user=settings.mysql_user,
        password=settings.mysql_password,
        database=database,
        charset="utf8mb4",
        autocommit=True,
    )


def create_database_and_user(settings: Settings, database: str) -> None:
    if not IDENTIFIER.match(database) or not IDENTIFIER.match(settings.mysql_user):
        raise ConfigurationError("Database and user names must be simple identifiers.")
    host = account_host(settings.mysql_host)
    admin = admin_connection(settings)
    try:
        with admin.cursor() as cursor:
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{database}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci"
            )
            password_literal = admin.escape(settings.mysql_password)
            cursor.execute(
                f"CREATE USER IF NOT EXISTS '{settings.mysql_user}'@'{host}' "
                f"IDENTIFIED BY {password_literal}"
            )
            cursor.execute(
                f"GRANT ALL PRIVILEGES ON `{database}`.* "
                f"TO '{settings.mysql_user}'@'{host}'"
            )
            cursor.execute("FLUSH PRIVILEGES")
    finally:
        admin.close()


def account_host(host: str) -> str:
    """Restrict provisioned application accounts to local connections."""
    if host.casefold() == "localhost":
        return "localhost"
    try:
        address = ipaddress.ip_address(host.strip("[]"))
    except ValueError as exc:
        raise ConfigurationError(
            "Automatic account provisioning supports localhost or a loopback IP only."
        ) from exc
    if not address.is_loopback:
        raise ConfigurationError(
            "Automatic account provisioning is restricted to loopback connections."
        )
    return str(address)


def reset_database(settings: Settings, database: str) -> None:
    if not IDENTIFIER.match(database):
        raise ConfigurationError("Database name must be a simple identifier.")
    admin = admin_connection(settings)
    try:
        with admin.cursor() as cursor:
            cursor.execute(f"DROP DATABASE IF EXISTS `{database}`")
            cursor.execute(
                f"CREATE DATABASE `{database}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci"
            )
    finally:
        admin.close()


def verify(settings: Settings, database: str) -> None:
    conn = app_connection(settings, database)
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT table_name, table_type FROM information_schema.tables "
                "WHERE table_schema = %s ORDER BY table_type, table_name",
                (database,),
            )
            rows = cursor.fetchall()
    finally:
        conn.close()
    tables = [name for name, kind in rows if kind == "BASE TABLE"]
    views = [name for name, kind in rows if kind == "VIEW"]
    print(f"Database: {database}")
    print(f"Base tables ({len(tables)}): {', '.join(tables)}")
    print(f"Views ({len(views)}): {', '.join(views)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Set up the BusinessPulse MySQL database")
    parser.add_argument("--database", help="Override MYSQL_DATABASE")
    parser.add_argument("--reset", action="store_true", help="Drop and recreate the database")
    parser.add_argument(
        "--skip-user-management",
        action="store_true",
        help="Do not create/grant the application user",
    )
    parser.add_argument("--files", nargs="*", default=list(DEFAULT_FILES))
    args = parser.parse_args()

    try:
        settings = get_settings()
    except ConfigurationError as exc:
        raise SystemExit(f"Configuration error: {exc}") from exc

    database = args.database or settings.mysql_database
    if not IDENTIFIER.match(database):
        raise SystemExit("Invalid database name; use letters, digits and underscores only.")
    if database == settings.mysql_test_database and not args.reset:
        print("Note: applying setup to the configured test database.")

    if args.reset:
        if settings.mysql_test_database == database:
            print(f"Resetting test database {database}...")
        else:
            print(f"Resetting database {database}...")
        reset_database(settings, database)
        if not args.skip_user_management:
            create_database_and_user(settings, database)
    elif not args.skip_user_management:
        create_database_and_user(settings, database)

    conn = app_connection(settings, database)
    all_errors: list[str] = []
    try:
        for file_name in args.files:
            statements = read_sql(file_name)
            executed, errors = execute_many(
                conn,
                statements,
                tolerate_index_errors=file_name == "indexes.sql",
                label=file_name,
            )
            print(f"{file_name}: {executed} statements executed")
            all_errors.extend(errors)
    finally:
        conn.close()

    if all_errors:
        print("\nErrors:")
        for error in all_errors:
            print(f"  - {error}")
        raise SystemExit(1)

    verify(settings, database)
    print("Setup complete.")


if __name__ == "__main__":
    main()
