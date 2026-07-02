---
title: Customer counting convention
type: concept
updated: 2025-08-01
sources: []
---

# Customer counting convention

## Rule

**"How many customers do we have" (or any unqualified count of
customers) means:**

```sql
SELECT COUNT(*) FROM customers WHERE status NOT IN ('banned', 'deleted');
```

This counts `active` and `pending` customers. It excludes `banned` and
`deleted` accounts, because those are soft-deleted / disabled accounts
that still exist as rows in [[tables/customers]] for referential and
audit purposes, but are not customers by any normal business meaning
of the word.

## When to deviate

Only count `banned`/`deleted` customers when the question **explicitly**
asks for them — e.g. "including banned and deleted accounts", "total
customer records ever created", "all customer accounts regardless of
status". In that case use a plain `COUNT(*)` with no status filter.

## Why this matters

A naive `COUNT(*) FROM customers` over-counts by including disabled
accounts that were never really "our customers" in the operational
sense — this can meaningfully inflate customer-count metrics (in this
dataset, by several accounts out of 50).

See [[tables/customers]] for the column definition.
