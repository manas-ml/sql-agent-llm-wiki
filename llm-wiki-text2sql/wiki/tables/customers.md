---
title: customers
type: table
updated: 2025-08-01
sources: [raw_sources/schema_dump.sql]
---

# customers

## Purpose

One row per registered customer account.

## Valid join paths

- `orders.customer_id = customers.customer_id` (see [[tables/orders]]).
- `orders_legacy.customer_id = customers.customer_id` (see
  [[tables/orders_legacy]]).

## Gotchas

- `status` has four values: `active`, `pending`, `banned`, `deleted`.
  `banned` and `deleted` are soft-delete states — the row still exists
  for referential/audit purposes but the account is not a "real"
  customer in the conventional sense.
- **Counting convention:** see [[concepts/customer-counting]] for the
  exact rule on which statuses count as "our customers" by default.
  Do not just `COUNT(*)` on this table for "how many customers do we
  have" — that silently includes banned and deleted accounts.

<!-- AUTO-GENERATED:SCHEMA START -->

*Auto-generated from live schema. 50 rows.*

| Column | Type | Not Null | Primary Key | Sample values |
|---|---|---|---|---|
| `customer_id` | INTEGER | no | yes | 1, 2, 3 |
| `name` | TEXT | yes | no | 'Val Patel', 'Parker Chen', 'Bay Lee' |
| `email` | TEXT | yes | no | 'val.patel1@example.com', 'parker.chen2@example.com', 'bay.lee3@example.com' |
| `signup_date` | TEXT | yes | no | '2021-02-21', '2021-10-13', '2021-06-28' |
| `status` | TEXT | yes | no | 'pending', 'active', 'banned' |

<!-- AUTO-GENERATED:SCHEMA END -->
