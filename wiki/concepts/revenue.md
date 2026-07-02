---
title: Revenue
type: concept
updated: 2025-08-01
sources: []
---

# Revenue

"Revenue" is ambiguous on its own — it can mean gross sales or sales
net of refunds. This page defines both and states which one to use by
default.

## Definitions

- **Gross revenue** for a period = `SUM(orders.total_amount)` for
  orders with `order_date` in that period. Only use `orders` (current,
  post-migration) unless the question explicitly asks for historical /
  all-time data — see [[tables/orders_legacy]].
- **Net revenue** for a period = gross revenue for that period, minus
  refunds issued against orders placed in that period:

  ```sql
  SELECT
    (SELECT COALESCE(SUM(o.total_amount), 0)
       FROM orders o WHERE o.order_date BETWEEN :start AND :end)
    -
    (SELECT COALESCE(SUM(r.amount), 0)
       FROM refunds r
       JOIN orders o ON r.order_id = o.order_id
       WHERE o.order_date BETWEEN :start AND :end) AS net_revenue;
  ```

  Refunds are attributed to the period of the **underlying order's**
  `order_date`, not the refund's own `refund_date` (see
  [[tables/refunds]]).

## Default: "revenue" alone means net revenue

**If a question says "revenue" without the word "gross," compute net
revenue** (gross minus refunds). Refunds are frequent and often
substantial in this business (roughly 7% of gross dollar volume
company-wide) — quoting gross when someone asks for "revenue" plain
overstates the number in a way that matters.

Only compute gross revenue when the question explicitly says "gross
revenue" or equivalent ("revenue before refunds", "total sales before
refunds").

## Period scoping

"This fiscal year", "last quarter", etc. must be resolved against the
business's fiscal calendar — see [[concepts/fiscal-calendar]], not the
standard Jan–Dec calendar year.

## Scope: current data only, by default

Both gross and net revenue calculations use `orders` (and `refunds`,
which only references `orders`) — never `orders_legacy` — unless the
question explicitly asks for historical or all-time figures. See
[[tables/orders_legacy]] for how to combine current and legacy totals
when that's explicitly requested.
