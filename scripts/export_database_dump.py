"""Create a portable MySQL dump without exposing credentials on the command line.

Usage:
    python scripts/export_database_dump.py

The dump contains the schema objects and data for the configured database. It
does not contain a CREATE DATABASE or USE statement, so it can be restored into
a separately-created database. Credentials are written to a temporary option file
that is deleted immediately after mysqldump exits.

This script is intentionally not run automatically by the import; produce the
dump after the final import and verify it on a restore copy.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analytics.config import ConfigurationError, Settings, get_settings  # noqa: E402


def find_mysqldump() -> str:
    candidates = [
        os.getenv("MYSQLDUMP_BIN", ""),
        shutil.which("mysqldump") or "",
        r"C:\wamp64\bin\mysql\mysql9.1.0\bin\mysqldump.exe",
        r"C:\Program Files\MySQL\MySQL Server 9.1\bin\mysqldump.exe",
        r"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqldump.exe",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return candidate
    raise FileNotFoundError(
        "mysqldump was not found. Install the MySQL client or set MYSQLDUMP_BIN "
        "to the full path of mysqldump.exe."
    )


def quote_option_value(value: str) -> str:
    """Quote a value for a MySQL option file."""
    cleaned = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{cleaned}"'


def strip_definers(sql: str) -> str:
    """Make view/trigger definers portable across users.

    MySQL dumps include ``DEFINER=`user`@`host``` clauses. A view restored by a
    different user can then fail with SELECT permission errors even when the new
    user owns the database. Removing the clause lets the restoring user become
    the definer. The dump is a portfolio artifact, not a production migration.
    """
    cleaned = re.sub(r"DEFINER=`[^`]*`@`[^`]*`\s*", "", sql)
    if "DEFINER=" in cleaned:
        raise RuntimeError("Dump still contains an unsupported DEFINER clause")
    return cleaned


def write_option_file(settings: Settings, path: Path) -> None:
    lines = [
        "[client]",
        f"host={quote_option_value(settings.mysql_host)}",
        f"port={settings.mysql_port}",
        f"user={quote_option_value(settings.mysql_user)}",
        f"password={quote_option_value(settings.mysql_password)}",
        "default-character-set=utf8mb4",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def export_dump(settings: Settings, output: Path) -> None:
    mysqldump = find_mysqldump()
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, option_name = tempfile.mkstemp(prefix="businesspulse_mysql_", suffix=".cnf")
    os.close(fd)
    option_path = Path(option_name)
    try:
        write_option_file(settings, option_path)
        command = [
            mysqldump,
            f"--defaults-extra-file={option_path}",
            "--single-transaction",
            "--quick",
            "--routines",
            "--triggers",
            "--no-tablespaces",
            "--set-gtid-purged=OFF",
            "--default-character-set=utf8mb4",
            settings.mysql_database,
        ]
        with output.open("wb") as handle:
            completed = subprocess.run(
                command,
                cwd=ROOT,
                stdout=handle,
                stderr=subprocess.PIPE,
            )
        if completed.returncode != 0:
            error = completed.stderr.decode("utf-8", errors="replace")[:1000]
            raise RuntimeError(f"mysqldump failed: {error}")
    finally:
        # The file contains a password; delete it even if the dump failed.
        option_path.unlink(missing_ok=True)

    if not output.exists() or output.stat().st_size == 0:
        raise RuntimeError("mysqldump produced an empty file")
    content = output.read_text(encoding="utf-8", errors="replace")
    if "CREATE TABLE" not in content:
        raise RuntimeError("Dump does not contain CREATE TABLE statements")
    if "INSERT INTO" not in content:
        raise RuntimeError("Dump does not contain data INSERT statements")
    output.write_text(strip_definers(content), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Export a BusinessPulse MySQL dump")
    parser.add_argument(
        "--output",
        default=str(ROOT / "database" / "businesspulse_dump.sql"),
    )
    args = parser.parse_args()
    try:
        settings = get_settings()
    except ConfigurationError as exc:
        raise SystemExit(f"Configuration error: {exc}") from exc

    output = Path(args.output)
    try:
        export_dump(settings, output)
    except (FileNotFoundError, RuntimeError) as exc:
        raise SystemExit(f"Dump failed: {exc}") from exc
    print(f"Dump written: {output}")
    print(f"Size: {output.stat().st_size:,} bytes")
    print("Restore it into a fresh database and verify counts before delivery.")


if __name__ == "__main__":
    main()
