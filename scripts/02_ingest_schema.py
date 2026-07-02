#!/usr/bin/env python3
"""
Introspect the live schema of data/sample.db and create/update one wiki
page per table under wiki/tables/.

This script owns exactly the block between the
  <!-- AUTO-GENERATED:SCHEMA START -->
  <!-- AUTO-GENERATED:SCHEMA END -->
markers in each table page (see wiki/SCHEMA.md for the convention). On
every run it regenerates that block from the live schema and sample
data, but leaves everything else on the page -- frontmatter, Purpose,
Valid join paths, Gotchas -- untouched. That's what makes the wiki
"incrementally maintained" rather than "regenerated from scratch": the
curated, resolved knowledge survives re-ingestion.

If a table has no existing wiki page at all, a minimal new page is
created with empty hand-authored sections for a human (or an agent
under supervision) to fill in later.
"""

import argparse
import os
import sqlite3

SCRIPT_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(SCRIPT_DIR, "..", "data", "sample.db")
WIKI_TABLES_DIR = os.path.join(SCRIPT_DIR, "..", "wiki", "tables")

START_MARKER = "<!-- AUTO-GENERATED:SCHEMA START -->"
END_MARKER = "<!-- AUTO-GENERATED:SCHEMA END -->"

SAMPLE_ROWS = 3


def get_tables(conn):
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    return [r[0] for r in rows]


def get_columns(conn, table):
    """Returns list of (cid, name, type, notnull, default, pk) via PRAGMA table_info."""
    return conn.execute(f"PRAGMA table_info({table})").fetchall()


def get_sample_values(conn, table, column, limit=SAMPLE_ROWS):
    rows = conn.execute(
        f"SELECT DISTINCT {column} FROM {table} WHERE {column} IS NOT NULL LIMIT {limit}"
    ).fetchall()
    return [r[0] for r in rows]


def render_schema_block(conn, table):
    columns = get_columns(conn, table)
    row_count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

    lines = [START_MARKER, "", f"*Auto-generated from live schema. {row_count} rows.*", ""]
    lines.append("| Column | Type | Not Null | Primary Key | Sample values |")
    lines.append("|---|---|---|---|---|")
    for cid, name, coltype, notnull, default, pk in columns:
        samples = get_sample_values(conn, table, name)
        sample_str = ", ".join(repr(s) for s in samples) if samples else "-"
        lines.append(
            f"| `{name}` | {coltype or '-'} | {'yes' if notnull else 'no'} | "
            f"{'yes' if pk else 'no'} | {sample_str} |"
        )
    lines.append("")
    lines.append(END_MARKER)
    return "\n".join(lines)


def default_page(table):
    """A minimal page for a table that has no wiki page yet."""
    return (
        "---\n"
        f"title: {table}\n"
        "type: table\n"
        "updated: (never hand-edited)\n"
        "sources: [raw_sources/schema_dump.sql]\n"
        "---\n\n"
        f"# {table}\n\n"
        "## Purpose\n\n"
        "TODO: describe what this table represents.\n\n"
        "## Valid join paths\n\n"
        "TODO: document every valid join path, including tempting-but-wrong ones.\n\n"
        "## Gotchas\n\n"
        "TODO: units, nullability traps, deprecation status, etc.\n\n"
        f"{START_MARKER}\n{END_MARKER}\n"
    )


def upsert_page(table, schema_block):
    path = os.path.join(WIKI_TABLES_DIR, f"{table}.md")

    if os.path.exists(path):
        with open(path, "r") as f:
            content = f.read()
        if START_MARKER in content and END_MARKER in content:
            pre = content.split(START_MARKER)[0]
            post = content.split(END_MARKER)[1]
            new_content = pre + schema_block + post
        else:
            # No markers yet on an otherwise hand-authored page: append the block.
            new_content = content.rstrip() + "\n\n" + schema_block + "\n"
        action = "updated"
    else:
        new_content = default_page(table).replace(
            f"{START_MARKER}\n{END_MARKER}", schema_block
        )
        action = "created"

    with open(path, "w") as f:
        f.write(new_content)
    return action


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()

    conn = sqlite3.connect(DB_PATH)
    os.makedirs(WIKI_TABLES_DIR, exist_ok=True)

    tables = get_tables(conn)
    print(f"Found {len(tables)} tables in {DB_PATH}: {', '.join(tables)}\n")

    for table in tables:
        block = render_schema_block(conn, table)
        action = upsert_page(table, block)
        print(f"  {action:8s} wiki/tables/{table}.md")

    conn.close()
    print("\nDone. Hand-authored sections (Purpose, Valid join paths, Gotchas) were left untouched.")


if __name__ == "__main__":
    main()
