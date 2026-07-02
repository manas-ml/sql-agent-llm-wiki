---
title: products
type: table
updated: 2025-08-01
sources: [raw_sources/schema_dump.sql]
---

# products

## Purpose

Product catalog: one row per sellable item, with category and price.

## Valid join paths

- **To order line items:** `order_items.product_id = products.product_id`
  (see [[tables/order_items]]).
- Products have no direct link to `orders`, `stores`, or `regions` —
  always go through `order_items`.

## Gotchas

- **`price_cents` is in cents (integer), not dollars.** This is the
  single most common unit trap in this schema. `orders.total_amount` is
  in dollars (decimal) — see [[tables/orders]]. Any query that combines
  `price_cents` with `total_amount`, or that reports `price_cents`
  directly as if it were a dollar figure, will be off by exactly 100x.
  - Conversion rule: **dollars = price_cents / 100.0** (use a float
    divisor so SQLite doesn't do integer division).
  - Example: a line-item's dollar value is
    `(order_items.quantity * products.price_cents) / 100.0`, not
    `order_items.quantity * products.price_cents`.
- `category` is free-text (e.g. `Electronics`, `Fitness`, `Home`,
  `Office`, `Bags`, `Accessories`) — no separate categories table.

<!-- AUTO-GENERATED:SCHEMA START -->

*Auto-generated from live schema. 30 rows.*

| Column | Type | Not Null | Primary Key | Sample values |
|---|---|---|---|---|
| `product_id` | INTEGER | no | yes | 1, 2, 3 |
| `name` | TEXT | yes | no | 'Wireless Mouse', 'Mechanical Keyboard', 'USB-C Hub' |
| `category` | TEXT | yes | no | 'Electronics', 'Accessories', 'Fitness' |
| `price_cents` | INTEGER | yes | no | 1999, 7999, 3499 |

<!-- AUTO-GENERATED:SCHEMA END -->
