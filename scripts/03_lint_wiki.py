#!/usr/bin/env python3
"""
Lint the wiki against the live schema of data/sample.db and report drift.

Three checks:
  1. Tables with no corresponding wiki/tables/<table>.md page.
  2. Wiki pages containing a backtick-quoted `table.column` reference
     where `table.column` no longer exists in the live schema (catches
     renamed/dropped columns after the wiki has gone stale).
  3. Orphaned pages: any wiki/**/*.md page that no other page links to
     via a [[wikilink]] (except wiki/index.md itself, which is the
     entry point and isn't expected to be linked from elsewhere).

--simulate-drift renames data/sample.db's orders.total_amount column to
orders.total_amount_usd (a realistic "we clarified the currency in the
column name" migration) so that a subsequent lint run demonstrably
finds the now-broken `orders.total_amount` references sprinkled across
the wiki. Run scripts/01_seed_db.py afterward to rebuild a clean
database before using the agents or eval suite again.
"""

import argparse
import os
import re
import sqlite3

SCRIPT_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(SCRIPT_DIR, "..", "data", "sample.db")
WIKI_DIR = os.path.join(SCRIPT_DIR, "..", "wiki")
WIKI_TABLES_DIR = os.path.join(WIKI_DIR, "tables")

DOTTED_REF_RE = re.compile(r"`([a-z_][a-z0-9_]*)\.([a-z_][a-z0-9_]*)`")
WIKILINK_RE = re.compile(r"\[\[([a-zA-Z0-9_/\-]+)\]\]")


def get_live_schema(conn):
    """Returns {table_name: set(column_names)}."""
    tables = [
        r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
    ]
    schema = {}
    for t in tables:
        cols = {row[1] for row in conn.execute(f"PRAGMA table_info({t})").fetchall()}
        schema[t] = cols
    return schema


def find_all_wiki_pages():
    pages = {}
    for root, _, files in os.walk(WIKI_DIR):
        for fname in files:
            if not fname.endswith(".md"):
                continue
            path = os.path.join(root, fname)
            rel = os.path.relpath(path, WIKI_DIR)
            # Wikilink key: path without extension, forward-slash separated.
            key = os.path.splitext(rel)[0].replace(os.sep, "/")
            with open(path) as f:
                pages[key] = f.read()
    return pages


def check_missing_pages(schema):
    findings = []
    for table in sorted(schema):
        page_path = os.path.join(WIKI_TABLES_DIR, f"{table}.md")
        if not os.path.exists(page_path):
            findings.append(f"MISSING PAGE: table `{table}` has no wiki/tables/{table}.md")
    return findings


def check_stale_column_refs(pages, schema):
    findings = []
    for page_key, content in sorted(pages.items()):
        for table, column in DOTTED_REF_RE.findall(content):
            if column == "md":
                continue  # backtick-quoted filename reference (e.g. `orders.md`), not a column
            if table not in schema:
                findings.append(
                    f"STALE REF: wiki/{page_key}.md references `{table}.{column}`, "
                    f"but table `{table}` no longer exists"
                )
            elif column not in schema[table]:
                findings.append(
                    f"STALE REF: wiki/{page_key}.md references `{table}.{column}`, "
                    f"but column `{column}` no longer exists on `{table}`"
                )
    return findings


def check_orphan_pages(pages):
    linked = set()
    for content in pages.values():
        for target in WIKILINK_RE.findall(content):
            linked.add(target)

    findings = []
    for page_key in sorted(pages):
        if page_key == "index":
            continue  # entry point, not expected to be linked from elsewhere
        if page_key not in linked:
            findings.append(f"ORPHAN: wiki/{page_key}.md has no incoming [[wikilink]]")
    return findings


def simulate_drift(conn):
    print("Simulating schema drift: renaming orders.total_amount -> orders.total_amount_usd\n")
    conn.execute("ALTER TABLE orders RENAME COLUMN total_amount TO total_amount_usd")
    conn.commit()


def run_lint(conn):
    schema = get_live_schema(conn)
    pages = find_all_wiki_pages()

    missing = check_missing_pages(schema)
    stale = check_stale_column_refs(pages, schema)
    orphans = check_orphan_pages(pages)

    print(f"Tables in live schema: {len(schema)}")
    print(f"Wiki pages found: {len(pages)}\n")

    for label, findings in [
        ("Missing wiki pages", missing),
        ("Stale column references", stale),
        ("Orphaned pages", orphans),
    ]:
        print(f"== {label} ({len(findings)}) ==")
        if findings:
            for f in findings:
                print(f"  - {f}")
        else:
            print("  none")
        print()

    total = len(missing) + len(stale) + len(orphans)
    print(f"Total issues: {total}")
    return total


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--simulate-drift", action="store_true",
        help="Rename orders.total_amount to orders.total_amount_usd in the live DB, "
             "then run the lint so the resulting stale references are visible immediately.",
    )
    args = parser.parse_args()

    conn = sqlite3.connect(DB_PATH)

    if args.simulate_drift:
        simulate_drift(conn)

    total = run_lint(conn)
    conn.close()

    if args.simulate_drift:
        print(
            "\nDrift simulated. Run `python scripts/01_seed_db.py` to rebuild a clean "
            "database before using the agents or eval suite again."
        )

    raise SystemExit(1 if total else 0)


if __name__ == "__main__":
    main()
