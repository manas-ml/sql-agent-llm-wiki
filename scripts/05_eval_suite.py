#!/usr/bin/env python3
"""
Runs a fixed set of 8 NL questions -- at least one per deliberate pitfall --
through both the baseline (schema-only) and wiki-grounded agents, executes
both generated SQL statements, compares results against a hardcoded expected
answer for each question, and prints a comparison table.

Expected answers were computed directly against data/sample.db (seed 42) and
are only valid for that exact dataset -- re-running 01_seed_db.py with the
same seed reproduces them.

Usage:
    ANTHROPIC_API_KEY=... python scripts/05_eval_suite.py [--model MODEL]
"""

import argparse
import importlib.util
import os
import sys

SCRIPT_DIR = os.path.dirname(__file__)


def _load_module(filename):
    """04_agent_wiki.py / 04_agent_baseline.py aren't valid module names
    (start with a digit) so they can't be `import`ed directly -- load by path."""
    path = os.path.join(SCRIPT_DIR, filename)
    spec = importlib.util.spec_from_file_location(filename[:-3], path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

agent_wiki = _load_module("04_agent_wiki.py")
agent_baseline = _load_module("04_agent_baseline.py")


# --- Fixed eval questions -----------------------------------------------
#
# Each entry: id, the NL question, which pitfall(s) it tests, and the
# expected answer, expressed either as a single scalar ("value") or a
# breakdown by region ("by_region"). See README.md "Results summary" for
# how these were derived from data/sample.db.

QUESTIONS = [
    {
        "id": "Q1",
        "question": "What were total sales by region in June 2025?",
        "pitfall": "wrong join path (orders -> warehouses vs orders -> stores)",
        "expected": {"by_region": {
            "Asia Pacific": 85.95,
            "Europe": 741.85,
            "Latin America": 1076.80,
            "Middle East & Africa": 1433.76,
        }},
    },
    {
        "id": "Q2",
        "question": "As of August 1, 2025, what were total sales by region last quarter?",
        "pitfall": "wrong join path + fiscal calendar (fiscal Q2 FY2025 = May-Jul 2025)",
        "expected": {"by_region": {
            "Asia Pacific": 2111.52,
            "Europe": 2700.48,
            "Latin America": 2726.43,
            "Middle East & Africa": 4310.22,
            "North America": 1555.53,
        }},
    },
    {
        "id": "Q3",
        "question": "What is the average line-item value (unit price times quantity) "
                     "across all order items, in dollars?",
        "pitfall": "unit mismatch (price_cents vs total_amount)",
        "expected": {"value": 104.40},
    },
    {
        "id": "Q4",
        "question": "How many customers do we have?",
        "pitfall": "soft-delete / status filtering (default excludes banned+deleted)",
        "expected": {"value": 42},
    },
    {
        "id": "Q5",
        "question": "How many customers do we have in total, including banned and deleted accounts?",
        "pitfall": "soft-delete / status filtering (explicit override)",
        "expected": {"value": 50},
    },
    {
        "id": "Q6",
        "question": "As of August 1, 2025, what is our net revenue for this fiscal year to date?",
        "pitfall": "ambiguous revenue metric (net = gross - refunds) + fiscal calendar",
        "expected": {"value": 22400.38},
    },
    {
        "id": "Q7",
        "question": "How many total orders have we processed?",
        "pitfall": "deprecated dataset inclusion (orders_legacy excluded by default)",
        "expected": {"value": 200},
    },
    {
        "id": "Q8",
        "question": "What is our total gross revenue across all orders, including historical "
                     "pre-migration data?",
        "pitfall": "deprecated dataset inclusion (explicit historical request)",
        "expected": {"value": 59841.16},
    },
]


def tolerance(expected_value: float) -> float:
    return max(0.5, abs(expected_value) * 0.01)


def extract_scalar_candidates(rows):
    for row in rows:
        for cell in row:
            try:
                yield float(cell)
            except (TypeError, ValueError):
                continue


def check_scalar(expected_value, columns, rows) -> bool:
    if rows is None:
        return False
    tol = tolerance(expected_value)
    return any(abs(c - expected_value) <= tol for c in extract_scalar_candidates(rows))


def check_by_region(expected_by_region, columns, rows) -> bool:
    if rows is None:
        return False
    for region, expected_amt in expected_by_region.items():
        tol = tolerance(expected_amt)
        found = False
        for row in rows:
            row_strs = [str(c) for c in row]
            if not any(region.lower() == s.lower() for s in row_strs):
                continue
            for cell in row:
                try:
                    val = float(cell)
                except (TypeError, ValueError):
                    continue
                if abs(val - expected_amt) <= tol:
                    found = True
                    break
            if found:
                break
        if not found:
            return False
    return True


def check_correct(expected: dict, columns, rows) -> bool:
    if "value" in expected:
        return check_scalar(expected["value"], columns, rows)
    return check_by_region(expected["by_region"], columns, rows)


def format_expected(expected: dict) -> str:
    if "value" in expected:
        return f"{expected['value']:,.2f}"
    return ", ".join(f"{r}={v:,.2f}" for r, v in expected["by_region"].items())


def format_actual(columns, rows) -> str:
    if rows is None:
        return "ERROR"
    if not rows:
        return "(no rows)"
    if len(rows) == 1 and len(rows[0]) == 1:
        return str(rows[0][0])
    return "; ".join(", ".join(str(v) for v in row) for row in rows[:6]) + (" ..." if len(rows) > 6 else "")


def run_agent(fn, *args):
    try:
        return fn(*args), None
    except Exception as e:
        return None, str(e)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=agent_wiki.DEFAULT_MODEL, help="Anthropic model name")
    args = parser.parse_args()

    results = []
    for q in QUESTIONS:
        print(f"Running {q['id']}: {q['question']}", file=sys.stderr)

        baseline_out, baseline_err = run_agent(agent_baseline.answer_question, q["question"], args.model)
        wiki_out, wiki_err = run_agent(agent_wiki.answer_question, q["question"], args.model)

        if baseline_err:
            b_columns, b_rows = None, baseline_err
        else:
            _, b_columns, b_rows = baseline_out

        if wiki_err:
            w_columns, w_rows = None, wiki_err
        else:
            _, w_columns, w_rows, _wiki_pages = wiki_out

        b_correct = False if baseline_err else check_correct(q["expected"], b_columns, b_rows)
        w_correct = False if wiki_err else check_correct(q["expected"], w_columns, w_rows)

        results.append({
            "id": q["id"],
            "question": q["question"],
            "pitfall": q["pitfall"],
            "baseline_result": "ERROR" if baseline_err else format_actual(b_columns, b_rows),
            "wiki_result": "ERROR" if wiki_err else format_actual(w_columns, w_rows),
            "expected": format_expected(q["expected"]),
            "baseline_correct": b_correct,
            "wiki_correct": w_correct,
        })

    print_table(results)


def print_table(results):
    def y_n(b):
        return "y" if b else "n"

    print()
    print(f"{'ID':4s} {'Pitfall':55s} {'Baseline':>10s} {'Wiki':>10s}")
    print("-" * 85)
    for r in results:
        print(f"{r['id']:4s} {r['pitfall'][:55]:55s} {y_n(r['baseline_correct']):>10s} {y_n(r['wiki_correct']):>10s}")
    print()

    print("Full detail:\n")
    header = ["question", "pitfall", "baseline result", "wiki result", "expected result",
              "baseline correct (y/n)", "wiki correct (y/n)"]
    print(" | ".join(header))
    print("-" * 100)
    for r in results:
        row = [
            r["question"], r["pitfall"], r["baseline_result"], r["wiki_result"],
            r["expected"], y_n(r["baseline_correct"]), y_n(r["wiki_correct"]),
        ]
        print(" | ".join(row))

    n = len(results)
    b_score = sum(1 for r in results if r["baseline_correct"])
    w_score = sum(1 for r in results if r["wiki_correct"])
    print(f"\nResults summary: baseline {b_score}/{n} correct, wiki-grounded {w_score}/{n} correct")


if __name__ == "__main__":
    main()
