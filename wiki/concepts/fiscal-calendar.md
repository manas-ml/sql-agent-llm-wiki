---
title: Fiscal calendar
type: concept
updated: 2025-08-01
sources: []
---

# Fiscal calendar

## Rule

**The business's fiscal year starts February 1, not January 1.**

- Fiscal Year N ("FY{N}") runs from **Feb 1 of year N** through
  **Jan 31 of year N+1**.
- Fiscal quarters within FY{N}:
  - **Q1:** Feb 1 – Apr 30
  - **Q2:** May 1 – Jul 31
  - **Q3:** Aug 1 – Oct 31
  - **Q4:** Nov 1 – Jan 31 (of year N+1)

Any question involving "this fiscal year," "last fiscal quarter," "Q2
FY2025," etc. must use these boundaries — **not** the standard
calendar-year quarters (Jan–Mar, Apr–Jun, Jul–Sep, Oct–Dec). The two
disagree by one month in every quarter boundary, so using calendar
quarters against a fiscal-quarter question silently shifts the date
window and changes the answer.

## Resolving relative dates

Relative phrases ("last quarter", "this fiscal year to date") must be
resolved against a stated or given reference/"as of" date — for
example, if a question says "as of August 1, 2025," then:

- "This fiscal year" = FY2025 = Feb 1, 2025 – Jan 31, 2026 (in
  progress; "to date" means through the reference date).
- "Last quarter" = the most recently **completed** fiscal quarter
  before the reference date. As of Aug 1, 2025 (which falls in fiscal
  Q3 FY2025, Aug–Oct), the last completed quarter is **fiscal Q2
  FY2025: May 1 – Jul 31, 2025**.

If a question gives no explicit reference date, ask for one or state
the assumption explicitly rather than silently using the SQL engine's
current date, since that makes the query's result non-reproducible.

## Why this matters

See [[concepts/revenue]] for revenue period-scoping and
[[tables/orders]] for the `order_date` column this all operates on.
Using calendar quarters instead of fiscal quarters shifts the query
window by exactly one month at each boundary, which changes both the
total and the region-by-region breakdown of any "last quarter" or
"this fiscal year" question.
