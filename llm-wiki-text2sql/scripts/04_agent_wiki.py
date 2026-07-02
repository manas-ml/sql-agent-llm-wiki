#!/usr/bin/env python3
"""
Wiki-grounded NL -> SQL agent. Retrieves relevant wiki pages via simple
keyword matching against page titles/content, builds a system prompt
from the raw schema PLUS that retrieved context, and asks Claude to
generate SQL.

This is the "LLM Wiki" side of the comparison: instead of re-deriving
join paths, unit conventions, and business definitions from the schema
alone, the agent reads them directly off curated wiki pages.

Usage:
    ANTHROPIC_API_KEY=... python scripts/04_agent_wiki.py "your question" [--model MODEL] [--top-k N]
"""

import argparse
import os
import re
import sqlite3
import sys

from _agent_common import DB_PATH, DEFAULT_MODEL, generate_sql, run_sql, format_result, get_raw_schema_text

SCRIPT_DIR = os.path.dirname(__file__)
WIKI_DIR = os.path.join(SCRIPT_DIR, "..", "wiki")

STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "of", "in", "on", "for",
    "to", "and", "or", "by", "our", "we", "what", "what's", "how", "many",
    "with", "do", "does", "this", "that", "as", "across", "all", "have",
    "has", "total", "average", "last", "per",
}

TOP_K_DEFAULT = 6

FRONTMATTER_RE = re.compile(r"\A---\n.*?\n---\n", re.DOTALL)


def tokenize(text: str) -> set:
    words = re.findall(r"[a-z0-9']+", text.lower())
    return {w for w in words if w not in STOPWORDS and len(w) > 1}


def load_wiki_pages() -> dict:
    """Returns {relative_path: content} for every wiki page except SCHEMA.md,
    index.md, and log.md (meta pages, not table/concept knowledge). YAML
    frontmatter (which mostly just contains a boilerplate date) is stripped
    before the content is used for retrieval scoring, but the full page
    (including frontmatter) is still what gets sent to the model."""
    pages = {}
    skip = {"SCHEMA.md", "index.md", "log.md"}
    for root, _, files in os.walk(WIKI_DIR):
        for fname in files:
            if not fname.endswith(".md") or fname in skip:
                continue
            path = os.path.join(root, fname)
            rel = os.path.relpath(path, WIKI_DIR)
            with open(path) as f:
                pages[rel] = f.read()
    return pages


def retrieve_relevant_pages(question: str, pages: dict, top_k: int) -> list:
    """Simple keyword-overlap retrieval: score each page by how many
    question keywords appear in its title or body, return the top_k
    highest-scoring pages with a nonzero score."""
    q_tokens = tokenize(question)
    scored = []
    for rel_path, content in pages.items():
        page_tokens = tokenize(FRONTMATTER_RE.sub("", content))
        title_tokens = tokenize(rel_path.replace("/", " ").replace(".md", "").replace("-", " "))
        score = len(q_tokens & page_tokens) + 2 * len(q_tokens & title_tokens)
        if score > 0:
            scored.append((score, rel_path))
    scored.sort(key=lambda x: (-x[0], x[1]))
    return [rel_path for _, rel_path in scored[:top_k]]


SYSTEM_PROMPT_TEMPLATE = """You are a text-to-SQL assistant for a SQLite e-commerce database.

Here is the raw database schema (table_name(column_name type, ...)):

{schema}

You also have access to a curated internal wiki that documents join
paths, unit conventions, and business definitions that are NOT
recoverable from the schema alone. Below are the wiki pages most
relevant to this question -- read them carefully and follow their
rules exactly (formulas, filters, join paths) when they apply:

{wiki_context}

Given a natural-language question, respond with a single SQL query that
answers it, wrapped in a ```sql code fence. Output only the SQL query,
no explanation."""

NO_WIKI_CONTEXT = "(No wiki pages matched this question's keywords.)"


def answer_question(question: str, model: str = DEFAULT_MODEL, top_k: int = TOP_K_DEFAULT):
    """Generates SQL for `question` grounded in retrieved wiki pages, executes
    it, and returns (sql, columns, rows, relevant_pages). Reused by main() and
    by 05_eval_suite.py."""
    conn = sqlite3.connect(DB_PATH)
    try:
        schema = get_raw_schema_text(conn)

        pages = load_wiki_pages()
        relevant = retrieve_relevant_pages(question, pages, top_k)

        if relevant:
            wiki_context = "\n\n---\n\n".join(f"### wiki/{rel}\n\n{pages[rel]}" for rel in relevant)
        else:
            wiki_context = NO_WIKI_CONTEXT

        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(schema=schema, wiki_context=wiki_context)
        sql = generate_sql(system_prompt, question, model)
        columns, result = run_sql(conn, sql)
    finally:
        conn.close()
    return sql, columns, result, relevant


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question", help="Natural-language question to answer")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Anthropic model name")
    parser.add_argument("--top-k", type=int, default=TOP_K_DEFAULT, help="Max wiki pages to retrieve")
    args = parser.parse_args()

    try:
        sql, columns, result, relevant = answer_question(args.question, args.model, args.top_k)
    except Exception as e:
        print(f"Error calling Anthropic API: {e}", file=sys.stderr)
        sys.exit(1)

    print("=== Wiki-grounded agent ===")
    print(f"Question: {args.question}")
    print(f"\nGenerated SQL:\n{sql}")
    print(f"\nWiki pages used: {', '.join(relevant) if relevant else '(none matched)'}")
    print(f"\nResult:\n{format_result(columns, result)}")


if __name__ == "__main__":
    main()
