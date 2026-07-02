---
title: Wiki Conventions
type: meta
updated: 2025-08-01
sources: []
---

# Wiki Conventions

This file defines the conventions for every other page in `wiki/`. It is
itself a wiki page (Layer 3 in the LLM-Wiki pattern: durable, curated
knowledge that agents read directly instead of re-deriving from raw
sources on every query).

## Frontmatter

Every page starts with YAML frontmatter:

```yaml
---
title: Human-readable page title
type: table | concept | meta
updated: YYYY-MM-DD          # last edit date
sources: [raw_sources/...]   # Layer 1 documents this page was derived from, if any
---
```

## Filenames

- Lowercase, hyphenated: `orders-legacy.md`, not `Orders_Legacy.md`.
- Table pages live in `wiki/tables/` and are named after the table:
  `wiki/tables/orders.md` documents the `orders` table.
- Concept pages live in `wiki/concepts/` and are named after the
  business concept: `wiki/concepts/revenue.md`.

## Linking

Use `[[wikilinks]]` (the page's filename without extension) to reference
another page, e.g. `[[tables/orders]]` or `[[concepts/revenue]]`. Every
page should link to at least one other page where relevant, so
`03_lint_wiki.py` can confirm it isn't orphaned.

## Required content for table pages

Every table page MUST contain, in addition to the auto-generated schema
section:

1. **Purpose** — one or two sentences on what the table represents.
2. **Valid join paths** — every join path an agent is likely to need,
   stated explicitly (`table_a.col = table_b.col`), INCLUDING join paths
   that look tempting but are wrong, with a one-line explanation of why
   they're wrong. Do not just document the correct path and stay silent
   on the wrong one — the wrong one is exactly what a schema-only agent
   will reach for.
3. **Gotchas** — units, nullability traps, deprecation status, or any
   other fact that isn't recoverable by looking at column names and
   types alone.

## Auto-generated vs. hand-authored content

`02_ingest_schema.py` owns everything between the markers

```
<!-- AUTO-GENERATED:SCHEMA START -->
...
<!-- AUTO-GENERATED:SCHEMA END -->
```

and will overwrite that block on every run. Everything outside those
markers (Purpose, Join Paths, Gotchas) is hand-authored and must never
be touched by the ingest script.

## Log discipline

Every substantive edit to a wiki page gets one line appended to
`wiki/log.md`: date, page, what changed, why.
