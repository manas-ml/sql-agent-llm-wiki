CREATE TABLE customers (
    customer_id INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    email       TEXT NOT NULL,
    signup_date TEXT NOT NULL,
    status      TEXT NOT NULL CHECK (status IN ('active','pending','banned','deleted'))
);

CREATE TABLE order_items (
    order_item_id INTEGER PRIMARY KEY,
    order_id      INTEGER NOT NULL REFERENCES orders(order_id),
    product_id    INTEGER NOT NULL REFERENCES products(product_id),
    quantity      INTEGER NOT NULL
);

CREATE TABLE orders (
    order_id     INTEGER PRIMARY KEY,
    customer_id  INTEGER NOT NULL REFERENCES customers(customer_id),
    store_id     INTEGER NOT NULL REFERENCES stores(store_id),
    warehouse_id INTEGER REFERENCES warehouses(warehouse_id),
    order_date   TEXT NOT NULL,
    total_amount REAL NOT NULL
);

CREATE TABLE orders_legacy (
    order_id     INTEGER PRIMARY KEY,
    customer_id  INTEGER NOT NULL,
    order_date   TEXT NOT NULL,
    total_amount REAL NOT NULL
);

CREATE TABLE products (
    product_id  INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    category    TEXT NOT NULL,
    price_cents INTEGER NOT NULL
);

CREATE TABLE refunds (
    refund_id   INTEGER PRIMARY KEY,
    order_id    INTEGER NOT NULL REFERENCES orders(order_id),
    amount      REAL NOT NULL,
    refund_date TEXT NOT NULL
);

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
