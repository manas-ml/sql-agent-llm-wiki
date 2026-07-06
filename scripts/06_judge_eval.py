#!/usr/bin/env python3
"""
LLM-as-judge eval, run as a fully separate process from 05_eval_suite.py.

05_eval_suite.py grades agents by exact/numeric match against a hardcoded
expected value per question -- solid ground truth, but blind to *why* an
answer is right or wrong (an agent can get a number right by luck via the
wrong join path and still score "correct"). This script instead asks an
LLM judge to grade each agent's generated SQL against a five-criterion
rubric: did it use the correct join path, apply the right filters, use
the right units/formula, actually use the wiki context it was given, and
does the executed result answer the question. Judge verdicts are a
qualitative, directional signal -- NOT validated ground truth like
05_eval_suite.py's hardcoded `expected` values.

This script only reads from _agent_common.py, 04_agent_wiki.py,
04_agent_baseline.py, and 05_eval_suite.py -- none of those files are
modified.

The agents under test still generate SQL via the Anthropic SDK (using
--model, default from _agent_common.DEFAULT_MODEL). The JUDGE itself runs
on GLM 5.2 via OpenRouter's OpenAI-compatible chat completions API, and is
not affected by --model. Judge auth requires the OPENROUTER_API_KEY env
var.

Usage:
    ANTHROPIC_API_KEY=... OPENROUTER_API_KEY=... \
        python scripts/06_judge_eval.py [--model MODEL]
"""

import argparse
import importlib.util
import json
import os
import re
import sys
import urllib.error
import urllib.request

from _agent_common import DEFAULT_MODEL, format_result

SCRIPT_DIR = os.path.dirname(__file__)

JUDGE_MODEL = "z-ai/glm-5.2"
JUDGE_MAX_TOKENS = 400
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def _load_module(filename):
    """04_agent_wiki.py / 04_agent_baseline.py / 05_eval_suite.py aren't
    valid module names (start with a digit) so they can't be `import`ed
    directly -- load by path, same trick 05_eval_suite.py uses."""
    path = os.path.join(SCRIPT_DIR, filename)
    spec = importlib.util.spec_from_file_location(filename[:-3], path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


agent_wiki = _load_module("04_agent_wiki.py")
agent_baseline = _load_module("04_agent_baseline.py")
eval_suite = _load_module("05_eval_suite.py")

QUESTIONS = eval_suite.QUESTIONS

CRITERIA = ["join_path", "filter_adherence", "unit_formula", "wiki_utilization", "answer_correctness"]
CRITERIA_LABELS = {
    "join_path": "Join",
    "filter_adherence": "Filter",
    "unit_formula": "Unit",
    "wiki_utilization": "WikiUse",
    "answer_correctness": "Answer",
}

JUDGE_SYSTEM_PROMPT = """You are grading a generated SQL query that attempts to answer a \
natural-language question about an e-commerce database. You will be given the question, \
the internal wiki context (if any) the agent was given as guidance, the SQL it generated, \
and the executed result of that SQL.

Score the SQL against five criteria. For each, respond with 0 (fails), 1 (partially \
correct), 2 (fully correct), or N/A (criterion does not apply to this question):

1. JOIN_PATH -- Did the SQL join through the correct table path for this question? \
0 = wrong table(s) joined, 1 = right tables but wrong/missing join condition, \
2 = matches the correct path exactly. N/A if the question needs no join.
2. FILTER_ADHERENCE -- Were required filters applied (soft-delete exclusion, \
deprecated/legacy-table exclusion or inclusion, fiscal-year boundaries, etc)? \
0 = rule ignored, 1 = partially applied, 2 = fully correct. N/A if no filter rule is \
relevant to this question.
3. UNIT_FORMULA -- Correct unit conversions and correct formula (e.g. cents vs dollars, \
gross vs net revenue). N/A if no unit/formula conversion is needed.
4. WIKI_UTILIZATION -- Given the wiki context provided, did the agent actually apply the \
relevant documented rule, or ignore it and do something schema-only would do? Always N/A \
if no wiki context was provided at all.
5. ANSWER_CORRECTNESS -- Does the executed result actually answer the question as asked \
(right grain, right filters reflected in the final numbers)? Never N/A.

Respond in EXACTLY this format, nothing else, no markdown:
JOIN_PATH: 0|1|2|N/A
FILTER_ADHERENCE: 0|1|2|N/A
UNIT_FORMULA: 0|1|2|N/A
WIKI_UTILIZATION: 0|1|2|N/A
ANSWER_CORRECTNESS: 0|1|2
VERDICT: PASS|FAIL
REASON: <one sentence citing the lowest-scoring applicable criterion>

VERDICT is PASS only if ANSWER_CORRECTNESS is 2 AND no applicable criterion scored 0. \
Otherwise VERDICT is FAIL."""

_FIELD_RE = {
    "join_path": re.compile(r"JOIN_PATH:\s*(0|1|2|N/A)", re.IGNORECASE),
    "filter_adherence": re.compile(r"FILTER_ADHERENCE:\s*(0|1|2|N/A)", re.IGNORECASE),
    "unit_formula": re.compile(r"UNIT_FORMULA:\s*(0|1|2|N/A)", re.IGNORECASE),
    "wiki_utilization": re.compile(r"WIKI_UTILIZATION:\s*(0|1|2|N/A)", re.IGNORECASE),
    "answer_correctness": re.compile(r"ANSWER_CORRECTNESS:\s*(0|1|2)", re.IGNORECASE),
}
_VERDICT_RE = re.compile(r"VERDICT:\s*(PASS|FAIL)", re.IGNORECASE)
_REASON_RE = re.compile(r"REASON:\s*(.+)", re.IGNORECASE)


def _parse_judge_response(text: str) -> dict:
    """Parses the fixed rubric format above; any missing/unparseable field
    falls back to "ERROR" rather than raising."""
    result = {}
    for field, pattern in _FIELD_RE.items():
        match = pattern.search(text)
        if not match:
            result[field] = "ERROR"
        else:
            val = match.group(1).upper()
            result[field] = val if val == "N/A" else int(val)

    verdict_match = _VERDICT_RE.search(text)
    result["verdict"] = verdict_match.group(1).upper() if verdict_match else "ERROR"

    reason_match = _REASON_RE.search(text)
    result["reason"] = reason_match.group(1).strip() if reason_match else "(unparseable judge response)"
    return result


def _error_result(message: str) -> dict:
    result = {field: "ERROR" for field in CRITERIA}
    result["verdict"] = "ERROR"
    result["reason"] = message
    return result


def _call_glm_judge(system_prompt: str, user_content: str) -> str:
    """Calls GLM 5.2 via OpenRouter's OpenAI-compatible chat completions
    API and returns the raw text response. Raises on any auth/HTTP/parse
    failure so judge_answer can catch it and surface an "ERROR" row
    instead of crashing the run."""
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY env var required to call GLM 5.2")

    payload = json.dumps({
        "model": JUDGE_MODEL,
        "max_tokens": JUDGE_MAX_TOKENS,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
    }).encode("utf-8")
    req = urllib.request.Request(
        OPENROUTER_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenRouter HTTP {e.code}: {detail}") from e

    choices = body.get("choices")
    if not choices:
        raise RuntimeError(f"OpenRouter returned no choices: {body}")
    content = choices[0].get("message", {}).get("content", "")
    if not content:
        raise RuntimeError(f"OpenRouter returned empty content: {body}")
    return content


def judge_answer(question: str, wiki_context: str, sql: str, result_text: str) -> dict:
    """Calls GLM 5.2 (via OpenRouter) to grade a generated SQL
    answer against the five-criterion rubric above. Returns a dict with keys
    join_path, filter_adherence, unit_formula, wiki_utilization,
    answer_correctness (each an int 0-2, "N/A", or "ERROR"), plus verdict
    ("PASS"/"FAIL"/"ERROR") and reason (str). Never raises -- API/parse
    failures surface as an all-"ERROR" dict so one bad judge call can't kill
    the run. The judge model is always GLM 5.2 and is not affected by --model,
    which controls only the SQL-generating agents."""
    user_content = (
        f"Question: {question}\n\n"
        f"Wiki context given to agent:\n{wiki_context or '(none -- no wiki access)'}\n\n"
        f"Generated SQL:\n{sql}\n\n"
        f"Executed result:\n{result_text}"
    )
    try:
        text = _call_glm_judge(JUDGE_SYSTEM_PROMPT, user_content)
        return _parse_judge_response(text)
    except Exception as e:
        return _error_result(str(e))


def reconstruct_wiki_context(question: str, top_k: int = agent_wiki.TOP_K_DEFAULT) -> str:
    """Rebuilds the same wiki_context string agent_wiki.answer_question()
    assembles internally, using that module's own public functions, so we
    don't have to modify 04_agent_wiki.py to expose it."""
    pages = agent_wiki.load_wiki_pages()
    relevant = agent_wiki.retrieve_relevant_pages(question, pages, top_k)
    if not relevant:
        return ""
    return "\n\n---\n\n".join(f"### wiki/{rel}\n\n{pages[rel]}" for rel in relevant)


def run_agent_safely(fn, *args):
    try:
        return fn(*args), None
    except Exception as e:
        return None, str(e)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Anthropic model name for SQL-generating agents only (judge always uses GLM 5.2)")
    args = parser.parse_args()

    rows = []
    for q in QUESTIONS:
        print(f"Judging {q['id']}: {q['question']}", file=sys.stderr)

        baseline_out, baseline_err = run_agent_safely(agent_baseline.answer_question, q["question"], args.model)
        wiki_out, wiki_err = run_agent_safely(agent_wiki.answer_question, q["question"], args.model)

        if baseline_err:
            b_judge = _error_result(f"agent error: {baseline_err}")
        else:
            b_sql, b_columns, b_rows = baseline_out
            b_judge = judge_answer(q["question"], "", b_sql, format_result(b_columns, b_rows))

        if wiki_err:
            w_judge = _error_result(f"agent error: {wiki_err}")
        else:
            w_sql, w_columns, w_rows, _ = wiki_out
            wiki_context = reconstruct_wiki_context(q["question"])
            w_judge = judge_answer(q["question"], wiki_context, w_sql, format_result(w_columns, w_rows))

        rows.append({"id": q["id"], "question": q["question"], "pitfall": q["pitfall"], "baseline": b_judge, "wiki": w_judge})

    print_report(rows)


def _fmt_score(val) -> str:
    return str(val)


def print_report(rows):
    print()
    print(f"{'ID':4s} {'Pitfall':55s} {'Verdict(B)':>11s} {'Verdict(W)':>11s}")
    print("-" * 85)
    for r in rows:
        print(f"{r['id']:4s} {r['pitfall'][:55]:55s} {r['baseline']['verdict']:>11s} {r['wiki']['verdict']:>11s}")

    print()
    print("Per-criterion breakdown (Join | Filter | Unit | WikiUse | Answer):")
    header = f"{'ID':4s} " + " ".join(f"{CRITERIA_LABELS[c]:>8s}" for c in CRITERIA) + "  ||  " + " ".join(f"{CRITERIA_LABELS[c]:>8s}" for c in CRITERIA)
    print(header)
    print(f"{'':4s} " + " ".join(f"{'(base)':>8s}" for _ in CRITERIA) + "  ||  " + " ".join(f"{'(wiki)':>8s}" for _ in CRITERIA))
    print("-" * len(header))
    for r in rows:
        b_scores = " ".join(f"{_fmt_score(r['baseline'][c]):>8s}" for c in CRITERIA)
        w_scores = " ".join(f"{_fmt_score(r['wiki'][c]):>8s}" for c in CRITERIA)
        print(f"{r['id']:4s} {b_scores}  ||  {w_scores}")

    print()
    print("Full detail (reasons):\n")
    for r in rows:
        print(f"{r['id']}: {r['question']}")
        print(f"  baseline: {r['baseline']['verdict']} -- {r['baseline']['reason']}")
        print(f"  wiki:     {r['wiki']['verdict']} -- {r['wiki']['reason']}")
        print()

    n = len(rows)
    b_pass = sum(1 for r in rows if r["baseline"]["verdict"] == "PASS")
    w_pass = sum(1 for r in rows if r["wiki"]["verdict"] == "PASS")
    print(f"Judge summary: baseline {b_pass}/{n} passed, wiki-grounded {w_pass}/{n} passed")

    print("\nPer-criterion average score (numeric scores only, N/A and ERROR excluded):")
    for c in CRITERIA:
        b_vals = [r["baseline"][c] for r in rows if isinstance(r["baseline"][c], int)]
        w_vals = [r["wiki"][c] for r in rows if isinstance(r["wiki"][c], int)]
        b_avg = f"{sum(b_vals) / len(b_vals):.1f}/2" if b_vals else "n/a"
        w_avg = f"{sum(w_vals) / len(w_vals):.1f}/2" if w_vals else "n/a"
        print(f"  {CRITERIA_LABELS[c]:8s} avg: baseline {b_avg:>6s}, wiki {w_avg:>6s}")


if __name__ == "__main__":
    main()
