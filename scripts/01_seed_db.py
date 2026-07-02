#!/usr/bin/env python3
"""
Build data/sample.db: a small e-commerce SQLite database, seeded
deterministically so the dataset (and therefore every downstream eval
result) is reproducible across runs.

Idempotent: re-running this script deletes and rebuilds the database
from scratch rather than appending to it.

The data is *deliberately* shaped to make each of the six wiki pitfalls
(see wiki/tables/*.md and wiki/concepts/*.md) a real trap:
  1. orders.warehouse_id is mostly NULL and, when present, often points
     at a warehouse in a different region than the order's store -- so
     joining orders -> warehouses -> regions silently drops and
     misattributes rows.
  2. products.price_cents is cents; orders.total_amount is dollars.
  3. customers.status includes banned/deleted rows that should not be
     counted as "our customers" by default.
  4. refunds are frequent/large enough that gross revenue and net
     revenue (gross - refunds) meaningfully diverge.
  5. order dates span multiple fiscal quarters (fiscal year starts
     Feb 1) so calendar-quarter math and fiscal-quarter math disagree.
  6. orders_legacy holds pre-migration orders that must be excluded
     from "current" totals by default.
"""

import os
import random
import sqlite3
from datetime import date, timedelta

SEED = 42
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "sample.db")

random.seed(SEED)

SCHEMA = """
CREATE TABLE regions (
    region_id   INTEGER PRIMARY KEY,
    name        TEXT NOT NULL
);

CREATE TABLE stores (
    store_id    INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    region_id   INTEGER NOT NULL REFERENCES regions(region_id)
);

CREATE TABLE warehouses (
    warehouse_id INTEGER PRIMARY KEY,
    name         TEXT NOT NULL,
    region_id    INTEGER NOT NULL REFERENCES regions(region_id)
);

CREATE TABLE customers (
    customer_id INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    email       TEXT NOT NULL,
    signup_date TEXT NOT NULL,
    status      TEXT NOT NULL CHECK (status IN ('active','pending','banned','deleted'))
);

CREATE TABLE products (
    product_id  INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    category    TEXT NOT NULL,
    price_cents INTEGER NOT NULL
);

CREATE TABLE orders (
    order_id     INTEGER PRIMARY KEY,
    customer_id  INTEGER NOT NULL REFERENCES customers(customer_id),
    store_id     INTEGER NOT NULL REFERENCES stores(store_id),
    warehouse_id INTEGER REFERENCES warehouses(warehouse_id),
    order_date   TEXT NOT NULL,
    total_amount REAL NOT NULL
);

CREATE TABLE order_items (
    order_item_id INTEGER PRIMARY KEY,
    order_id      INTEGER NOT NULL REFERENCES orders(order_id),
    product_id    INTEGER NOT NULL REFERENCES products(product_id),
    quantity      INTEGER NOT NULL
);

CREATE TABLE refunds (
    refund_id   INTEGER PRIMARY KEY,
    order_id    INTEGER NOT NULL REFERENCES orders(order_id),
    amount      REAL NOT NULL,
    refund_date TEXT NOT NULL
);

CREATE TABLE orders_legacy (
    order_id     INTEGER PRIMARY KEY,
    customer_id  INTEGER NOT NULL,
    order_date   TEXT NOT NULL,
    total_amount REAL NOT NULL
);
"""

REGION_NAMES = ["North America", "Europe", "Asia Pacific", "Latin America", "Middle East & Africa"]

STORE_NAMES = [
    "Downtown Flagship", "Riverside Mall", "Airport Kiosk", "Harbor Plaza",
    "Uptown Corner", "Central Station", "West End Outlet", "Lakeside Store",
    "Old Town Shop", "Northgate Center",
]

WAREHOUSE_NAMES = [
    "Regional DC 1", "Regional DC 2", "Overflow Depot", "Coastal Fulfillment",
    "Inland Hub", "Express Sort Center", "Bulk Storage A", "Bulk Storage B",
]

FIRST_NAMES = [
    "Alex", "Jordan", "Taylor", "Morgan", "Casey", "Riley", "Jamie", "Avery",
    "Quinn", "Drew", "Skyler", "Reese", "Rowan", "Emerson", "Hayden", "Parker",
    "Sawyer", "Finley", "Dakota", "Charlie", "Sam", "Bailey", "Kendall", "Peyton",
    "Blake", "Cameron", "Devon", "Elliot", "Frankie", "Harper", "Jesse", "Kai",
    "Lane", "Marley", "Noel", "Ollie", "Pat", "Remy", "Shay", "Toby",
    "Val", "Wren", "Ash", "Bay", "Cy", "Dane", "Ezra", "Fox", "Gale", "Iris",
]
LAST_NAMES = [
    "Nguyen", "Smith", "Garcia", "Patel", "Kim", "Johnson", "Lopez", "Chen",
    "Brown", "Davis", "Martinez", "Wilson", "Anderson", "Taylor", "Moore",
    "Jackson", "Martin", "Lee", "Perez", "Thompson",
]

PRODUCT_CATALOG = [
    ("Wireless Mouse", "Electronics", 1999),
    ("Mechanical Keyboard", "Electronics", 7999),
    ("USB-C Hub", "Electronics", 3499),
    ("Noise Cancelling Headphones", "Electronics", 14999),
    ("Bluetooth Speaker", "Electronics", 5499),
    ("Smartwatch", "Electronics", 19999),
    ("Laptop Stand", "Accessories", 2999),
    ("Webcam 1080p", "Electronics", 4499),
    ("Phone Case", "Accessories", 1499),
    ("Screen Protector", "Accessories", 999),
    ("Yoga Mat", "Fitness", 2499),
    ("Dumbbell Set 20lb", "Fitness", 4999),
    ("Resistance Bands", "Fitness", 1799),
    ("Water Bottle 32oz", "Fitness", 1299),
    ("Running Shoes", "Fitness", 8999),
    ("Ceramic Mug", "Home", 899),
    ("French Press", "Home", 3299),
    ("Throw Blanket", "Home", 2999,),
    ("Scented Candle", "Home", 1199),
    ("Desk Lamp", "Home", 3999,),
    ("Notebook Set", "Office", 799),
    ("Fountain Pen", "Office", 2499),
    ("Desk Organizer", "Office", 1999),
    ("Sticky Notes Pack", "Office", 499),
    ("Whiteboard 24x36", "Office", 4599),
    ("Backpack", "Bags", 5999),
    ("Duffel Bag", "Bags", 4499),
    ("Laptop Sleeve", "Bags", 2299),
    ("Travel Pouch Set", "Bags", 1699),
    ("Tote Bag", "Bags", 1999),
]

STATUS_WEIGHTS = [("active", 35), ("pending", 5), ("banned", 5), ("deleted", 5)]

# Order dates span mid-2024 through end-of-July 2025, giving full
# coverage of fiscal Q3 FY2024 through fiscal Q2 FY2025 (fiscal year
# starts Feb 1). Eval questions anchor "as of" 2025-08-01 so "last
# fiscal quarter" resolves to fiscal Q2 FY2025 = May 1 - Jul 31 2025,
# which is deliberately offset by one month from calendar Q2 2025
# (Apr-Jun) so calendar-quarter math gives a visibly different answer.
ORDER_START = date(2024, 6, 1)
ORDER_END = date(2025, 7, 31)

LEGACY_START = date(2022, 1, 1)
LEGACY_END = date(2023, 5, 31)


def random_date(start: date, end: date) -> date:
    span = (end - start).days
    return start + timedelta(days=random.randint(0, span))


def weighted_choice(pairs):
    values, weights = zip(*pairs)
    return random.choices(values, weights=weights, k=1)[0]


def build_regions(cur):
    for i, name in enumerate(REGION_NAMES, start=1):
        cur.execute("INSERT INTO regions VALUES (?, ?)", (i, name))
    return list(range(1, len(REGION_NAMES) + 1))


def build_stores(cur, region_ids):
    store_region = {}
    for i, name in enumerate(STORE_NAMES, start=1):
        # Roughly two stores per region.
        region_id = region_ids[(i - 1) % len(region_ids)]
        cur.execute("INSERT INTO stores VALUES (?, ?, ?)", (i, name, region_id))
        store_region[i] = region_id
    return store_region


def build_warehouses(cur, region_ids):
    warehouse_region = {}
    for i, name in enumerate(WAREHOUSE_NAMES, start=1):
        region_id = region_ids[(i - 1) % len(region_ids)]
        cur.execute("INSERT INTO warehouses VALUES (?, ?, ?)", (i, name, region_id))
        warehouse_region[i] = region_id
    return warehouse_region


def build_customers(cur):
    statuses = []
    for i in range(1, 51):
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        name = f"{first} {last}"
        email = f"{first.lower()}.{last.lower()}{i}@example.com"
        signup = random_date(date(2021, 1, 1), date(2025, 6, 1))
        status = weighted_choice(STATUS_WEIGHTS)
        statuses.append(status)
        cur.execute(
            "INSERT INTO customers VALUES (?, ?, ?, ?, ?)",
            (i, name, email, signup.isoformat(), status),
        )
    return statuses


def build_products(cur):
    for i, (name, category, price_cents) in enumerate(PRODUCT_CATALOG, start=1):
        cur.execute("INSERT INTO products VALUES (?, ?, ?, ?)", (i, name, category, price_cents))


def build_orders(cur, store_region, warehouse_region, num_customers, num_stores, num_warehouses):
    """
    Generates 200 orders. warehouse_id is:
      - NULL for ~55% of orders (never captured pre-2025 point-of-sale
        rollout in most stores), and
      - for the remaining ~45%, a warehouse chosen WITHOUT regard to
        the order's store region about half the time (overflow /
        cross-region fulfillment), so region joins through warehouse_id
        are wrong even when non-null.
    total_amount is a plausible dollar total loosely derived from the
    order's line items, generated after order_items in a second pass.
    """
    order_store = {}
    order_dates = {}
    for order_id in range(1, 201):
        customer_id = random.randint(1, num_customers)
        store_id = random.randint(1, num_stores)
        order_date = random_date(ORDER_START, ORDER_END)

        if random.random() < 0.55:
            warehouse_id = None
        else:
            if random.random() < 0.5:
                # Same-region warehouse (the "usually right, but not
                # reliable" case that makes the trap realistic).
                region_id = store_region[store_id]
                candidates = [w for w, r in warehouse_region.items() if r == region_id]
                warehouse_id = random.choice(candidates) if candidates else random.randint(1, num_warehouses)
            else:
                # Cross-region overflow fulfillment: wrong region on purpose.
                warehouse_id = random.randint(1, num_warehouses)

        order_store[order_id] = store_id
        order_dates[order_id] = order_date
        cur.execute(
            "INSERT INTO orders (order_id, customer_id, store_id, warehouse_id, order_date, total_amount) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (order_id, customer_id, store_id, warehouse_id, order_date.isoformat(), 0.0),
        )
    return order_store, order_dates


def build_order_items(cur, num_orders, num_products):
    """~500 order_items across 200 orders (2-3 line items per order),
    and returns each order's dollar total computed from
    products.price_cents so total_amount is internally consistent."""
    order_totals = {oid: 0 for oid in range(1, num_orders + 1)}
    item_id = 1
    prices = {}
    for pid, (_, _, price_cents) in enumerate(PRODUCT_CATALOG, start=1):
        prices[pid] = price_cents

    for order_id in range(1, num_orders + 1):
        n_items = random.choice([1, 2, 2, 3, 3, 4])
        for _ in range(n_items):
            product_id = random.randint(1, num_products)
            quantity = random.randint(1, 4)
            cur.execute(
                "INSERT INTO order_items VALUES (?, ?, ?, ?)",
                (item_id, order_id, product_id, quantity),
            )
            order_totals[order_id] += prices[product_id] * quantity
            item_id += 1
    return order_totals


def finalize_order_totals(cur, order_totals):
    """Convert accumulated cents to dollars and write onto orders.total_amount."""
    for order_id, cents in order_totals.items():
        dollars = round(cents / 100.0, 2)
        cur.execute("UPDATE orders SET total_amount = ? WHERE order_id = ?", (dollars, order_id))
    return {oid: round(c / 100.0, 2) for oid, c in order_totals.items()}


def build_refunds(cur, order_totals_dollars, num_orders):
    """~30 refunds, sized so gross vs. net revenue meaningfully diverge
    (average refund is a substantial fraction of the order, not a
    rounding error)."""
    refund_id = 1
    refund_orders = random.sample(range(1, num_orders + 1), k=30)
    for order_id in refund_orders:
        order_total = order_totals_dollars[order_id]
        # Refund between 20% and 100% of the order total.
        fraction = random.uniform(0.2, 1.0)
        amount = round(order_total * fraction, 2)
        cur.execute("SELECT order_date FROM orders WHERE order_id = ?", (order_id,))
        order_date_str = cur.fetchone()[0]
        order_date_obj = date.fromisoformat(order_date_str)
        # Refund happens 1-21 days after the order, capped at ORDER_END.
        refund_date = order_date_obj + timedelta(days=random.randint(1, 21))
        if refund_date > ORDER_END:
            refund_date = ORDER_END
        cur.execute(
            "INSERT INTO refunds VALUES (?, ?, ?, ?)",
            (refund_id, order_id, amount, refund_date.isoformat()),
        )
        refund_id += 1


def build_orders_legacy(cur, num_customers):
    for order_id in range(1, 41):
        customer_id = random.randint(1, num_customers)
        order_date = random_date(LEGACY_START, LEGACY_END)
        total_amount = round(random.uniform(15, 400), 2)
        cur.execute(
            "INSERT INTO orders_legacy VALUES (?, ?, ?, ?)",
            (order_id, customer_id, order_date.isoformat(), total_amount),
        )


def main():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.executescript(SCHEMA)

    region_ids = build_regions(cur)
    store_region = build_stores(cur, region_ids)
    warehouse_region = build_warehouses(cur, region_ids)
    build_customers(cur)
    build_products(cur)
    order_store, order_dates = build_orders(
        cur, store_region, warehouse_region,
        num_customers=50, num_stores=len(STORE_NAMES), num_warehouses=len(WAREHOUSE_NAMES),
    )
    order_totals_cents = build_order_items(cur, num_orders=200, num_products=len(PRODUCT_CATALOG))
    order_totals_dollars = finalize_order_totals(cur, order_totals_cents)
    build_refunds(cur, order_totals_dollars, num_orders=200)
    build_orders_legacy(cur, num_customers=50)

    conn.commit()

    # Sanity-print row counts so the pitfalls are visibly present.
    for table in ["regions", "stores", "warehouses", "customers", "products",
                  "orders", "order_items", "refunds", "orders_legacy"]:
        n = cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"{table:16s} {n:5d} rows")

    null_wh = cur.execute("SELECT COUNT(*) FROM orders WHERE warehouse_id IS NULL").fetchone()[0]
    print(f"orders.warehouse_id NULL: {null_wh}/200")

    conn.close()
    print(f"\nWrote {DB_PATH}")


if __name__ == "__main__":
    main()
