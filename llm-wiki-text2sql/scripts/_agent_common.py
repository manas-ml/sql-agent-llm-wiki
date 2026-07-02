"""
Shared helpers for 04_agent_wiki.py and 04_agent_baseline.py.

Not a pipeline stage itself (leading underscore keeps it out of numeric
run order) -- just the plumbing both agents need: DB introspection, an
Anthropic API call that turns NL + context into SQL, and SQL execution.
"""

import os
import re
import sqlite3

import anthropic

SCRIPT_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(SCRIPT_DIR, "..", "data", "sample.db")

DEFAULT_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-opus-4-8")

SQL_BLOCK_RE = re.compile(r"```(?:sql)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def get_raw_schema_text(conn: sqlite3.Connection) -> str:
    """Bare PRAGMA-derived schema: table/column names and types only.
    No descriptions, no gotchas -- this is what the baseline agent sees."""
    tables = [
        r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
    ]
    lines = []
    for table in tables:
        cols = conn.execute(f"PRAGMA table_info({table})").fetchall()
        col_strs = [f"{name} {coltype}" for _, name, coltype, *_ in cols]
        lines.append(f"{table}({', '.join(col_strs)})")
    return "\n".join(lines)


def extract_sql(response_text: str) -> str:
    """Pull SQL out of a fenced code block; fall back to the raw text
    if the model didn't fence it."""
    match = SQL_BLOCK_RE.search(response_text)
    sql = match.group(1).strip() if match else response_text.strip()
    return sql.rstrip(";").strip()


def generate_sql(system_prompt: str, question: str, model: str) -> str:
    """Calls the Anthropic API with the given system prompt + NL question,
    returns the extracted SQL string. Requires ANTHROPIC_API_KEY in env."""
    client = anthropic.Anthropic()
    response = client.messages.create(
        model=model,
        max_tokens=1024,
        system=system_prompt,
        messages=[{"role": "user", "content": question}],
    )
    text = "".join(block.text for block in response.content if block.type == "text")
    return extract_sql(text)


def run_sql(conn: sqlite3.Connection, sql: str):
    """Executes SQL and returns (column_names, rows) or (None, error_message)."""
    try:
        cur = conn.execute(sql)
        columns = [d[0] for d in cur.description] if cur.description else []
        rows = cur.fetchall()
        return columns, rows
    except sqlite3.Error as e:
        return None, str(e)


def format_result(columns, rows_or_error) -> str:
    if columns is None:
        return f"ERROR: {rows_or_error}"
    if not rows_or_error:
        return "(no rows)"
    header = " | ".join(columns)
    body = "\n".join(" | ".join(str(v) for v in row) for row in rows_or_error)
    return f"{header}\n{body}"
