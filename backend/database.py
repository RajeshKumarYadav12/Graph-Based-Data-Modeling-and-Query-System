"""
database.py – SQLite schema setup and query execution for Order-to-Cash graph system.
"""
import sqlite3
import os
from typing import Any

DB_PATH = os.getenv("DB_PATH", "./data/otc.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Create all tables if they don't exist."""
    conn = get_connection()
    cur = conn.cursor()

    cur.executescript("""
    -- Customers / Business Partners
    CREATE TABLE IF NOT EXISTS customers (
        customer_id     TEXT PRIMARY KEY,
        full_name       TEXT,
        grouping        TEXT,
        category        TEXT,
        language        TEXT,
        created_by      TEXT,
        creation_date   TEXT
    );

    -- Sales Order Headers
    CREATE TABLE IF NOT EXISTS sales_orders (
        sales_order         TEXT PRIMARY KEY,
        order_type          TEXT,
        sales_org           TEXT,
        dist_channel        TEXT,
        division            TEXT,
        sold_to_party       TEXT,
        creation_date       TEXT,
        created_by          TEXT,
        total_net_amount    REAL,
        currency            TEXT,
        delivery_status     TEXT,
        billing_status      TEXT,
        total_credit_check_status TEXT,
        pricing_date        TEXT,
        requested_delivery  TEXT,
        payment_terms       TEXT,
        incoterms           TEXT,
        incoterms_location  TEXT,
        FOREIGN KEY (sold_to_party) REFERENCES customers(customer_id)
    );

    -- Sales Order Items
    CREATE TABLE IF NOT EXISTS sales_order_items (
        id                      INTEGER PRIMARY KEY AUTOINCREMENT,
        sales_order             TEXT,
        sales_order_item        TEXT,
        item_category           TEXT,
        material                TEXT,
        requested_quantity      REAL,
        quantity_unit           TEXT,
        net_amount              REAL,
        currency                TEXT,
        material_group          TEXT,
        production_plant        TEXT,
        storage_location        TEXT,
        billing_block            TEXT,
        UNIQUE(sales_order, sales_order_item),
        FOREIGN KEY (sales_order) REFERENCES sales_orders(sales_order)
    );

    -- Delivery Headers
    CREATE TABLE IF NOT EXISTS delivery_headers (
        delivery_document   TEXT PRIMARY KEY,
        shipping_point      TEXT,
        overall_goods_mvt   TEXT,
        overall_picking     TEXT,
        overall_pod         TEXT,
        goods_mvt_date      TEXT,
        creation_date       TEXT,
        delivery_block      TEXT,
        billing_block       TEXT
    );

    -- Delivery Items
    CREATE TABLE IF NOT EXISTS delivery_items (
        id                          INTEGER PRIMARY KEY AUTOINCREMENT,
        delivery_document           TEXT,
        delivery_item               TEXT,
        plant                       TEXT,
        storage_location            TEXT,
        material                    TEXT,
        actual_qty                  REAL,
        qty_unit                    TEXT,
        ref_sales_order             TEXT,
        ref_sales_order_item        TEXT,
        last_change_date            TEXT,
        UNIQUE(delivery_document, delivery_item),
        FOREIGN KEY (delivery_document) REFERENCES delivery_headers(delivery_document),
        FOREIGN KEY (ref_sales_order) REFERENCES sales_orders(sales_order)
    );

    -- Billing Document Headers
    CREATE TABLE IF NOT EXISTS billing_headers (
        billing_document        TEXT PRIMARY KEY,
        billing_type            TEXT,
        billing_date            TEXT,
        creation_date           TEXT,
        is_cancelled            INTEGER DEFAULT 0,
        cancelled_doc           TEXT,
        total_net_amount        REAL,
        currency                TEXT,
        company_code            TEXT,
        fiscal_year             TEXT,
        accounting_document     TEXT,
        sold_to_party           TEXT
    );

    -- Billing Document Items
    CREATE TABLE IF NOT EXISTS billing_items (
        id                          INTEGER PRIMARY KEY AUTOINCREMENT,
        billing_document            TEXT,
        billing_item                TEXT,
        material                    TEXT,
        billing_quantity            REAL,
        qty_unit                    TEXT,
        net_amount                  REAL,
        currency                    TEXT,
        ref_sales_order             TEXT,
        ref_sales_order_item        TEXT,
        UNIQUE(billing_document, billing_item),
        FOREIGN KEY (billing_document) REFERENCES billing_headers(billing_document)
    );

    -- Journal Entries (Accounting Documents)
    CREATE TABLE IF NOT EXISTS journal_entries (
        id                          INTEGER PRIMARY KEY AUTOINCREMENT,
        company_code                TEXT,
        fiscal_year                 TEXT,
        accounting_document         TEXT,
        accounting_doc_item         TEXT,
        gl_account                  TEXT,
        reference_document          TEXT,
        cost_center                 TEXT,
        profit_center               TEXT,
        currency                    TEXT,
        amount_in_currency          REAL,
        company_currency            TEXT,
        amount_in_company_currency  REAL,
        posting_date                TEXT,
        document_date               TEXT,
        doc_type                    TEXT,
        assignment_ref              TEXT,
        customer                    TEXT,
        financial_account_type      TEXT,
        clearing_date               TEXT,
        clearing_doc                TEXT,
        UNIQUE(accounting_document, accounting_doc_item)
    );

    -- Products / Materials
    CREATE TABLE IF NOT EXISTS products (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        product         TEXT,
        plant           TEXT,
        profit_center   TEXT,
        mrp_type        TEXT,
        country_origin  TEXT,
        UNIQUE(product, plant)
    );

    CREATE INDEX IF NOT EXISTS idx_so_sold_to ON sales_orders(sold_to_party);
    CREATE INDEX IF NOT EXISTS idx_soi_so ON sales_order_items(sales_order);
    CREATE INDEX IF NOT EXISTS idx_di_do ON delivery_items(delivery_document);
    CREATE INDEX IF NOT EXISTS idx_di_ref ON delivery_items(ref_sales_order);
    CREATE INDEX IF NOT EXISTS idx_bi_bd ON billing_items(billing_document);
    CREATE INDEX IF NOT EXISTS idx_bi_ref ON billing_items(ref_sales_order);
    CREATE INDEX IF NOT EXISTS idx_je_ref ON journal_entries(reference_document);
    CREATE INDEX IF NOT EXISTS idx_bh_acct ON billing_headers(accounting_document);
    CREATE INDEX IF NOT EXISTS idx_prod_p ON products(product);
    """)

    conn.commit()
    conn.close()
    print("[DB] Schema initialized.")


def execute_query(sql: str, params: tuple = ()) -> list[dict]:
    """Execute a SELECT query and return rows as list of dicts."""
    conn = get_connection()
    try:
        cur = conn.execute(sql, params)
        rows = [dict(r) for r in cur.fetchall()]
        return rows
    finally:
        conn.close()


def get_schema() -> str:
    """Return the DB schema as a string for LLM prompting."""
    return """
DATABASE SCHEMA (SQLite):

TABLE: customers
  - customer_id (TEXT PK), full_name, grouping, category, language, created_by, creation_date

TABLE: sales_orders
  - sales_order (TEXT PK), order_type, sales_org, dist_channel, division
  - sold_to_party → customers.customer_id
  - creation_date, created_by, total_net_amount, currency
  - delivery_status ('C'=Complete, 'A'=Not started, 'B'=Partial)
  - billing_status, pricing_date, requested_delivery, payment_terms, incoterms, incoterms_location

TABLE: sales_order_items
  - sales_order → sales_orders, sales_order_item, item_category
  - material, requested_quantity, quantity_unit, net_amount, currency
  - material_group, production_plant, storage_location, billing_block

TABLE: delivery_headers
  - delivery_document (TEXT PK), shipping_point
  - overall_goods_mvt ('C'=Posted, blank=Not posted)
  - overall_picking, overall_pod, goods_mvt_date, creation_date
  - delivery_block, billing_block

TABLE: delivery_items
  - delivery_document → delivery_headers, delivery_item
  - plant, storage_location, material
  - actual_qty, qty_unit
  - ref_sales_order → sales_orders, ref_sales_order_item

TABLE: billing_headers
  - billing_document (TEXT PK), billing_type, billing_date, creation_date
  - is_cancelled (0/1), cancelled_doc, total_net_amount, currency
  - company_code, fiscal_year, accounting_document
  - sold_to_party → customers.customer_id

TABLE: billing_items
  - billing_document → billing_headers, billing_item
  - material, billing_quantity, qty_unit, net_amount, currency
  - ref_sales_order → sales_orders, ref_sales_order_item

TABLE: journal_entries
  - accounting_document, accounting_doc_item
  - company_code, fiscal_year, gl_account
  - reference_document (= billing_document)
  - cost_center, profit_center, currency
  - amount_in_currency, company_currency, amount_in_company_currency
  - posting_date, document_date, doc_type
  - customer → customers.customer_id
  - clearing_date, clearing_doc

TABLE: products
  - product (material code), plant, profit_center, mrp_type, country_origin

KEY RELATIONSHIPS:
  - sales_orders.sold_to_party → customers.customer_id
  - sales_order_items.sales_order → sales_orders.sales_order
  - delivery_items.ref_sales_order → sales_orders.sales_order
  - delivery_items.ref_sales_order_item → sales_order_items.sales_order_item
  - billing_items.ref_sales_order → sales_orders.sales_order
  - billing_headers.accounting_document → journal_entries.accounting_document
  - journal_entries.reference_document → billing_headers.billing_document
  - sales_order_items.material = products.product
  - billing_items.material = products.product

FLOW: Customer → SalesOrder → SalesOrderItem → DeliveryItem → DeliveryHeader
      SalesOrderItem → BillingItem → BillingHeader → JournalEntry
"""
