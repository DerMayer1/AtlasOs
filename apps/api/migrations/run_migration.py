from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).resolve().parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply AtlasOS SQL migrations.")
    parser.add_argument(
        "migrations",
        nargs="*",
        help="Optional migration filenames. Defaults to every numbered SQL file.",
    )
    return parser.parse_args()


def migration_paths(names: list[str]) -> list[Path]:
    if not names:
        return sorted(MIGRATIONS_DIR.glob("[0-9][0-9][0-9]_*.sql"))

    paths = []
    for name in names:
        path = Path(name)
        if not path.is_absolute():
            path = MIGRATIONS_DIR / path.name
        if not path.exists():
            raise FileNotFoundError(f"Migration not found: {path}")
        paths.append(path)
    return paths


def main() -> None:
    args = parse_args()
    database_url = os.environ.get("SUPABASE_DB_URL")
    if not database_url:
        raise SystemExit("SUPABASE_DB_URL is required.")

    paths = migration_paths(args.migrations)
    if not paths:
        raise SystemExit("No migrations found.")

    bootstrap_sql = """
    create table if not exists public.schema_migrations (
      name text primary key,
      applied_at timestamptz not null default now()
    );
    """
    run_psql(database_url, sql=bootstrap_sql)

    for path in paths:
        result = run_psql(
            database_url,
            sql=(
                "select exists("
                "select 1 from public.schema_migrations "
                f"where name = '{sql_literal(path.name)}'"
                ");"
            ),
            capture_output=True,
        )
        if result.stdout.strip() == "t":
            print(f"Skipping {path.name} (already applied)")
            continue

        print(f"Applying {path.name}...")
        run_psql(database_url, file=path)
        run_psql(
            database_url,
            sql=(
                "insert into public.schema_migrations (name) "
                f"values ('{sql_literal(path.name)}');"
            ),
        )
        print(f"Applied {path.name}")


def sql_literal(value: str) -> str:
    return value.replace("'", "''")


def run_psql(
    database_url: str,
    *,
    sql: str | None = None,
    file: Path | None = None,
    capture_output: bool = False,
) -> subprocess.CompletedProcess[str]:
    command = ["psql", database_url, "--set", "ON_ERROR_STOP=1"]
    if sql is not None:
        command.extend(["--tuples-only", "--no-align", "--command", sql])
    elif file is not None:
        command.extend(["--file", str(file)])
    else:
        raise ValueError("sql or file is required")

    try:
        return subprocess.run(
            command,
            check=True,
            capture_output=capture_output,
            text=True,
        )
    except FileNotFoundError as exc:
        raise SystemExit(
            "psql was not found. Install PostgreSQL client tools and retry."
        ) from exc


if __name__ == "__main__":
    main()
