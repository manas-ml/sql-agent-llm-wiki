# llm-wiki-text2sql

A self-contained proof-of-concept demonstrating Andrej Karpathy's "LLM Wiki"
pattern applied to a text-to-SQL agent.

**The pattern:** instead of an agent re-deriving schema semantics from
scratch on every query (plain RAG-over-schema), a persistent, structured
markdown wiki is built once and incrementally maintained. It captures
*resolved* knowledge — join paths, unit conventions, business definitions —
that the agent reads directly instead of re-inferring from column names
and types alone.

This project builds a small e-commerce SQLite database with six deliberate
pitfalls baked into the schema and data, then compares two NL-to-SQL agents
head to head: one grounded only in the raw schema, one grounded in a curated
wiki. The wiki agent should get every pitfall right; the schema-only agent
should plausibly get most of them wrong.

## The six pitfalls

| # | Pitfall | Where it's resolved |
|---|---|---|
| 1 | Wrong join path: `orders.warehouse_id` is nullable and semantically wrong for region reporting; the correct path is `orders → stores → regions` | [`wiki/tables/orders.md`](wiki/tables/orders.md) |
| 2 | Unit mismatch: `products.price_cents` is cents, `orders.total_amount` is dollars | [`wiki/tables/products.md`](wiki/tables/products.md) |
| 3 | Soft-delete filtering: `customers.status` includes `banned`/`deleted`, excluded from counts by default | [`wiki/concepts/customer-counting.md`](wiki/concepts/customer-counting.md) |
| 4 | Ambiguous "revenue": gross vs. net (minus refunds); unqualified "revenue" means net | [`wiki/concepts/revenue.md`](wiki/concepts/revenue.md) |
| 5 | Fiscal year starts Feb 1, not Jan 1 | [`wiki/concepts/fiscal-calendar.md`](wiki/concepts/fiscal-calendar.md) |
| 6 | `orders_legacy` is a pre-migration archive, excluded from "current" totals by default | [`wiki/tables/orders_legacy.md`](wiki/tables/orders_legacy.md) |

## Project structure

```
llm-wiki-text2sql/
├── data/                    # generated sample.db lives here
├── raw_sources/             # immutable schema dump (Layer 1)
├── wiki/
│   ├── SCHEMA.md            # wiki conventions (Layer 3)
│   ├── index.md
│   ├── log.md
│   ├── tables/*.md          # one page per table
│   └── concepts/*.md        # customer-counting, revenue, fiscal-calendar
├── scripts/
│   ├── 01_seed_db.py        # builds data/sample.db (deterministic, seed=42)
│   ├── 02_ingest_schema.py  # introspects DB, updates wiki/tables/*.md
│   ├── 03_lint_wiki.py      # flags drift between live schema and wiki
│   ├── 04_agent_wiki.py     # NL -> SQL, grounded in wiki context
│   ├── 04_agent_baseline.py # NL -> SQL, grounded only in raw schema
│   ├── 05_eval_suite.py     # runs both agents over 8 questions, scores them
│   └── _agent_common.py     # shared helpers (not a pipeline stage)
├── requirements.txt
└── README.md
```

## Setup

```bash
pip install -r requirements.txt
python scripts/01_seed_db.py
```

This creates `data/sample.db` with 5 regions, 10 stores, 8 warehouses, 50
customers, 30 products, 200 orders, ~500 order_items, 30 refunds, and 40
legacy orders — deterministic (fixed random seed), so every run produces
identical data. Steps 1–3 (seed, ingest, lint) and reading the wiki files
directly need no API key; only `04_agent_wiki.py`, `04_agent_baseline.py`,
and `05_eval_suite.py` need `ANTHROPIC_API_KEY` in the environment.

## 1. Inspect the schema ingest

```bash
python scripts/02_ingest_schema.py
cat wiki/tables/orders.md
```

`02_ingest_schema.py` introspects the live schema via `PRAGMA table_info`
and writes an auto-generated column/type/sample-value table into each page,
between `<!-- AUTO-GENERATED:SCHEMA START/END -->` markers. Everything
outside those markers — Purpose, Valid join paths, Gotchas — is
hand-authored and untouched by re-running the script; that's what makes the
wiki *incrementally maintained* rather than regenerated from scratch. Try
running it twice in a row and diffing `wiki/tables/*.md` — nothing changes
on the second run.

## 2. Run the two agents directly (optional)

```bash
export ANTHROPIC_API_KEY=sk-ant-...
python scripts/04_agent_baseline.py "How many customers do we have?"
python scripts/04_agent_wiki.py "How many customers do we have?"
```

Both print the generated SQL, the wiki pages used (baseline: none), and the
query results, so you can see the difference in context — and therefore in
generated SQL — directly.

## 3. Run the eval suite

```bash
python scripts/05_eval_suite.py
```

Runs 8 fixed NL questions (at least one per pitfall) through both agents,
executes both generated SQL statements against `data/sample.db`, and prints
a comparison table: question | pitfall tested | baseline result | wiki
result | expected result | baseline correct (y/n) | wiki correct (y/n).

### Results summary

The harness itself (retrieval → SQL execution → scoring against hardcoded
expected answers) is verified end-to-end with representative correct and
incorrect SQL for all 8 questions — feeding the "correct" query for each
question scores **8/8**, and feeding a plausible schema-only "wrong" query
(warehouse join, unconverted cents, unfiltered customer count, calendar
instead of fiscal quarters, `orders_legacy` mishandled) scores **0/8** — so
the expected answers and the comparison logic are validated. What has *not*
been run in this environment is a live model: no `ANTHROPIC_API_KEY` was
available here, so the actual baseline-vs-wiki numbers from real Claude
completions are not filled in below. Run `python scripts/05_eval_suite.py`
with a real key and paste the final line here:

```
Results summary: baseline X/8 correct, wiki-grounded Y/8 correct
```

## 4. Walk through the pitfalls

**Pitfall 1 — wrong join path (Q1: "total sales by region in June 2025").**
A schema-only agent sees `orders.warehouse_id` and `warehouses.region_id`
and has no reason not to join through it — it's the only other
`region_id`-shaped path visible in the raw schema. That join is wrong for
two independent reasons: `warehouse_id` is NULL on ~55% of orders, and even
when set, the fulfilling warehouse is frequently in a different region than
the order's store (cross-region overflow routing). [`wiki/tables/orders.md`](wiki/tables/orders.md)
states explicitly: *"To region — CORRECT PATH: `orders.store_id =
stores.store_id`, then `stores.region_id = regions.region_id`"* and spells
out why the warehouse path is tempting but wrong. The wiki agent retrieves
that page (and `wiki/tables/stores.md`) and joins through stores instead.

**Pitfall 2 — unit mismatch (Q3: "average line-item value... in dollars").**
`order_items` has no price column; the schema-only agent has to look up
`products.price_cents` — and nothing in the schema says it's *cents*.
Multiplying `quantity * price_cents` and reporting it as a dollar figure is
off by exactly 100x. [`wiki/tables/products.md`](wiki/tables/products.md)
states the unit and the literal conversion rule (`price_cents / 100.0`),
and [`wiki/tables/order_items.md`](wiki/tables/order_items.md) repeats the
exact formula for a line item's dollar value.

**Pitfall 4 — ambiguous revenue (Q6: "net revenue for this fiscal year to
date").** A schema-only agent sees `orders.total_amount` and a `refunds`
table with no indication they're related in the definition of "revenue" —
it will most likely just `SUM(orders.total_amount)`, which is *gross*, not
*net*. [`wiki/concepts/revenue.md`](wiki/concepts/revenue.md) defines both
formulas explicitly and states the convention: *"If a question says
'revenue' without the word 'gross,' compute net revenue."* Refunds are
~7% of gross dollar volume in the seed data — enough to meaningfully move
the number if you get this wrong.

**Pitfall 5 — fiscal calendar (also Q6, and Q2).** The business's fiscal
year starts February 1. A schema-only agent has no way to know this and
will use the calendar year/quarter, which is offset by one month at every
boundary. [`wiki/concepts/fiscal-calendar.md`](wiki/concepts/fiscal-calendar.md)
states the exact quarter boundaries and shows how to resolve "last quarter"
against a given reference date.

**Pitfall 6 — deprecated dataset (Q7: "how many total orders have we
processed").** The schema-only agent sees both `orders` (200 rows) and
`orders_legacy` (40 rows) and has no signal that the latter is deprecated —
a plausible failure is `UNION`-ing them or adding the counts, landing on
240. [`wiki/tables/orders_legacy.md`](wiki/tables/orders_legacy.md) states
it's excluded from current totals by default and only included when a
question explicitly asks for historical/all-time data (tested separately
by Q8).

## 5. Lint the wiki / demonstrate drift detection

```bash
python scripts/03_lint_wiki.py                 # clean: 0 issues
python scripts/03_lint_wiki.py --simulate-drift # renames orders.total_amount -> total_amount_usd, re-lints
```

`--simulate-drift` renames a live column and immediately re-runs the lint,
so you see the before/after in one command — going from 0 issues to 4
stale `` `orders.total_amount` `` references across `wiki/tables/orders_legacy.md`
(x2), `wiki/tables/products.md`, and `wiki/tables/refunds.md`. Run
`python scripts/01_seed_db.py` afterward to rebuild a clean database before
using the agents or eval suite again.

The linter checks three things: tables with no wiki page, wiki pages that
reference a `` `table.column` `` that no longer exists in the live schema,
and pages with no incoming `[[wikilink]]` from any other page.

## How wiki retrieval works

`04_agent_wiki.py` does simple keyword-overlap retrieval (no embeddings,
no vector DB): it tokenizes the question, tokenizes each wiki page's title
and body (stripping YAML frontmatter first), scores each page by token
overlap (title matches weighted 2x), and includes the top-K (default 6)
pages with a nonzero score in the system prompt. This is intentionally
simple — the demonstration is about grounding in curated, resolved
knowledge, not about retrieval sophistication.

## Constraints

- Python 3, stdlib `sqlite3` for the database, `anthropic` SDK for LLM
  calls — no other required external services.
- No API key required for seeding, ingesting, or linting.
- Deterministic data generation (fixed seed) for reproducible results.
- The eval questions with relative dates ("last quarter", "this fiscal
  year") are anchored to an explicit "as of August 1, 2025" reference in
  the question text, so results don't drift with the real calendar date.
