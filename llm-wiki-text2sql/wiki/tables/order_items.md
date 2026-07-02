---
title: order_items
type: table
updated: 2025-08-01
sources: [raw_sources/schema_dump.sql]
---

# order_items

## Purpose

Line items within an order: one row per (order, product) purchase,
with quantity.

## Valid join paths

- `order_items.order_id = orders.order_id` (see [[tables/orders]]).
- `order_items.product_id = products.product_id` (see
  [[tables/products]]).

## Gotchas

- There is **no unit-price column** on `order_items` — the price must
  be looked up from `products.price_cents` (in cents; see
  [[tables/products]] for the conversion rule). Do not assume the
  order's `total_amount` divided evenly across its line items; line
  items can have different prices and quantities.
- `quantity` is an integer count, always >= 1.
- A line item's dollar value is
  `(order_items.quantity * products.price_cents) / 100.0`.

<!-- AUTO-GENERATED:SCHEMA START -->

*Auto-generated from live schema. 496 rows.*

| Column | Type | Not Null | Primary Key | Sample values |
|---|---|---|---|---|
| `order_item_id` | INTEGER | no | yes | 1, 2, 3 |
| `order_id` | INTEGER | yes | no | 1, 2, 3 |
| `product_id` | INTEGER | yes | no | 5, 24, 28 |
| `quantity` | INTEGER | yes | no | 2, 4, 3 |

<!-- AUTO-GENERATED:SCHEMA END -->
