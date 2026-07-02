#!/usr/bin/env python3
"""
Baseline NL -> SQL agent. Grounded ONLY in the raw PRAGMA-derived schema:
table and column names and types. No descriptions, no gotchas, no wiki.

This is the "plain RAG-over-schema" / no-wiki side of the comparison --
everything it gets wrong that 04_agent_wiki.py gets right is the point
of this demo.

Usage:
    ANTHROPIC_API_KEY=... python scripts/04_agent_baseline.py "your question" [--model MODEL]
"""

import argparse
import sqlite3
import sys

from _agent_common import DB_PATH, DEFAULT_MODEL, generate_sql, run_sql, format_result, get_raw_schema_text

SYSTEM_PROMPT_TEMPLATE = """You are a text-to-SQL assistant for a SQLite e-commerce database.

Here is the raw database schema (table_name(column_name type, ...)):

{schema}

Given a natural-language question, respond with a single SQL query that
answers it, wrapped in a ```sql code fence. Output only the SQL query,
no explanation."""


def answer_question(question: str, model: str = DEFAULT_MODEL):
    """Generates SQL for `question` using only the raw schema, executes it,
    and returns (sql, columns, rows). Reused by main() and by 05_eval_suite.py."""
    conn = sqlite3.connect(DB_PATH)
    try:
        schema = get_raw_schema_text(conn)
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(schema=schema)
        sql = generate_sql(system_prompt, question, model)
        columns, result = run_sql(conn, sql)
    finally:
        conn.close()
    return sql, columns, result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question", help="Natural-language question to answer")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Anthropic model name")
    args = parser.parse_args()

    try:
        sql, columns, result = answer_question(args.question, args.model)
    except Exception as e:
        print(f"Error calling Anthropic API: {e}", file=sys.stderr)
        sys.exit(1)

    print("=== Baseline agent (schema only, no wiki) ===")
    print(f"Question: {args.question}")
    print(f"\nGenerated SQL:\n{sql}")
    print("\nWiki pages used: (none -- baseline has no wiki access)")
    print(f"\nResult:\n{format_result(columns, result)}")


if __name__ == "__main__":
    main()
