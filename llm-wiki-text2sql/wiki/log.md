---
title: Wiki Change Log
type: meta
updated: 2025-08-01
sources: []
---

# Wiki Change Log

Append-only. Newest entries at the bottom. One line per substantive
change: date, page, what changed, why.

- 2025-08-01 — `wiki/SCHEMA.md` — created. Established frontmatter,
  filename, linking, and auto-generated-section conventions for the
  wiki.
- 2025-08-01 — `wiki/tables/orders.md` — created. Documented the
  `orders -> stores -> regions` correct join path and the
  `orders -> warehouses -> regions` trap (nulls + cross-region
  overflow routing), plus the dollars-vs-cents unit note and the
  orders_legacy exclusion rule.
- 2025-08-01 — `wiki/tables/products.md` — created. Documented
  `price_cents` unit and the `/100.0` conversion rule.
- 2025-08-01 — `wiki/tables/orders_legacy.md` — created. Documented
  that legacy orders have no store/warehouse columns and are excluded
  from current totals by default.
- 2025-08-01 — `wiki/tables/customers.md` — created. Pointed to the
  customer-counting convention for the `status` column.
- 2025-08-01 — `wiki/tables/stores.md`, `wiki/tables/warehouses.md`,
  `wiki/tables/regions.md` — created. Cross-referenced the region
  join-path trap documented on `orders.md`.
- 2025-08-01 — `wiki/tables/order_items.md`, `wiki/tables/refunds.md`
  — created. Documented the line-item price lookup and refund
  attribution rule for net revenue.
- 2025-08-01 — `wiki/concepts/customer-counting.md` — created. Defined
  "how many customers" as excluding `banned`/`deleted` by default.
- 2025-08-01 — `wiki/concepts/revenue.md` — created. Defined gross vs.
  net revenue and established that unqualified "revenue" means net.
- 2025-08-01 — `wiki/concepts/fiscal-calendar.md` — created. Defined
  the Feb 1 fiscal year start and fiscal quarter boundaries.
- 2025-08-01 — `wiki/index.md` — created. Indexed all pages above.
