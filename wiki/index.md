---
title: Wiki Index
type: meta
updated: 2025-08-01
sources: []
---

# Wiki Index

## Meta

- [[SCHEMA]] — conventions for writing and maintaining this wiki.

## Tables

- [[tables/customers]] — customer accounts; see the soft-delete status
  convention.
- [[tables/products]] — product catalog; prices are in **cents**.
- [[tables/stores]] — storefronts, the correct path from an order to a
  region.
- [[tables/warehouses]] — fulfillment warehouses; NOT a reliable path
  to an order's region.
- [[tables/regions]] — region lookup table.
- [[tables/orders]] — the transactional core; documents the
  store-vs-warehouse region join trap and the units used for
  `total_amount`.
- [[tables/order_items]] — order line items; no unit-price column, look
  up price from `products`.
- [[tables/refunds]] — refunds against orders; needed for net revenue.
- [[tables/orders_legacy]] — pre-migration archive; excluded from
  current totals by default.

## Concepts

- [[concepts/customer-counting]] — which customer statuses count as
  "our customers" by default.
- [[concepts/revenue]] — gross vs. net revenue, and which one "revenue"
  means by default.
- [[concepts/fiscal-calendar]] — the fiscal year starts Feb 1, not
  Jan 1; fiscal quarter boundaries.

## Log

- [[log]] — append-only history of changes to this wiki.
