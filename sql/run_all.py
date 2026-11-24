"""Exécute toute la partie SQL : import, puis les scripts sql/0*.sql dans l'ordre.

Les requêtes précédées d'un commentaire « -- name: ... » sont affichées
avec leurs résultats. L'ensemble est enregistré dans outputs/sql_results.txt.

Usage : uv run python sql/run_all.py

Les scripts .sql n'utilisent que du SQL standard SQLite : ils peuvent aussi être
exécutés avec la ligne de commande, après l'import :
    sqlite3 data/saveurs.db ".read sql/01_views.sql"
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pandas as pd

from import_data import DB_PATH, PROJECT_ROOT, import_all

SQL_DIR = Path(__file__).resolve().parent
OUTPUT_PATH = PROJECT_ROOT / "outputs" / "sql_results.txt"


def split_statements(script: str) -> list[tuple[str | None, str]]:
    """Découpe un script en instructions, chacune avec son titre « -- name: »."""
    statements, buffer, title = [], [], None

    for line in script.splitlines():
        stripped = line.strip()
        if stripped.startswith("-- name:"):
            title = stripped.removeprefix("-- name:").strip()
        buffer.append(line)

        candidate = "\n".join(buffer)
        if stripped and not stripped.startswith("--") and sqlite3.complete_statement(candidate):
            statements.append((title, candidate))
            buffer, title = [], None

    return statements


def run_script(connection: sqlite3.Connection, path: Path, log: list[str]) -> None:
    log.append(f"\n{'=' * 80}\n{path.name}\n{'=' * 80}")

    for title, statement in split_statements(path.read_text(encoding="utf-8")):
        cursor = connection.execute(statement)
        if cursor.description is None:
            if title:
                log.append(f"[ok] {title}")
            continue

        columns = [column[0] for column in cursor.description]
        result = pd.DataFrame(cursor.fetchall(), columns=columns)
        log.append(f"\n--- {title or 'query'} ({len(result)} rows)")
        log.append(result.to_string(index=False) if len(result) else "(no rows)")


def main() -> None:
    import_all()

    log: list[str] = []
    with pd.option_context("display.width", 200, "display.max_colwidth", 60):
        with sqlite3.connect(DB_PATH) as connection:
            for path in sorted(SQL_DIR.glob("0*.sql")):
                run_script(connection, path, log)

    output = "\n".join(log)
    OUTPUT_PATH.parent.mkdir(exist_ok=True)
    OUTPUT_PATH.write_text(output + "\n", encoding="utf-8")
    print(output)
    print(f"\nResults saved to {OUTPUT_PATH.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    sys.exit(main())
