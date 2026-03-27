"""
data_processor.py – Parse the PDF dataset and load records into SQLite.
Handles all entity types: SalesOrder, SalesOrderItem, Delivery, BillingDoc,
JournalEntry, Customer, Product.
"""
import json
import os
import sqlite3
import re
from pypdf import PdfReader
from database import get_connection, DB_PATH


def _parse_float(val) -> float | None:
    try:
        return float(val) if val not in (None, "", "null") else None
    except (ValueError, TypeError):
        return None


def _parse_bool(val) -> int:
    if isinstance(val, bool):
        return 1 if val else 0
    if isinstance(val, str):
        return 1 if val.lower() in ("true", "1", "yes") else 0
    return 0


def extract_json_objects_from_pdf(pdf_path: str) -> list[dict]:
    """
    Extract all JSON objects from the PDF dataset.
    The PDF contains JSONL-style records (one JSON object per page roughly).
    """
    print(f"[DataProcessor] Reading PDF: {pdf_path}")
    reader = PdfReader(pdf_path)
    full_text = ""
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        full_text += text + "\n"
        if i % 100 == 0:
            print(f"  ... page {i}/{len(reader.pages)}")

    print(f"[DataProcessor] Extracted {len(full_text):,} chars. Parsing JSON objects...")

    objects = []
    depth = 0
    current = ""
    in_string = False
    escape_next = False

    for char in full_text:
        if escape_next:
            current += char
            escape_next = False
            continue
        if char == '\\' and in_string:
            current += char
            escape_next = True
            continue
        if char == '"':
            in_string = not in_string
            if depth > 0:
                current += char
            continue
        if not in_string:
            if char == '{':
                depth += 1
                current += char
            elif char == '}':
                depth -= 1
                current += char
                if depth == 0 and current.strip():
                    try:
                        obj = json.loads(current.strip())
                        if isinstance(obj, dict) and len(obj) > 0:
                            objects.append(obj)
                    except json.JSONDecodeError:
                        pass
                    current = ""
            elif depth > 0:
                current += char
        else:
            if depth > 0:
                current += char

    print(f"[DataProcessor] Parsed {len(objects)} JSON objects.")
    return objects


def classify_object(obj: dict) -> str:
    """Classify a JSON object into an entity type."""
    keys = set(obj.keys())

    if 'glAccount' in keys and 'accountingDocument' in keys:
        return 'JournalEntry'
    # BillingItem: has billingDocumentItem and material (and usually referenceSdDocument)
    if 'billingDocumentItem' in keys and 'material' in keys:
        return 'BillingItem'
    # BillingHeader: has billingDocumentType but NOT billingDocumentItem
    if 'billingDocumentType' in keys and 'billingDocumentItem' not in keys:
        return 'BillingHeader'
    if 'deliveryDocumentItem' in keys:
        return 'DeliveryItem'
    if 'deliveryDocument' in keys and 'shippingPoint' in keys:
        return 'DeliveryHeader'
    if 'salesOrderItem' in keys and 'material' in keys and 'salesOrderItemCategory' in keys:
        return 'SalesOrderItem'
    if 'salesOrder' in keys and 'salesOrderType' in keys and 'soldToParty' in keys:
        return 'SalesOrder'
    if 'scheduleLine' in keys and 'salesOrder' in keys:
        return 'ScheduleLine'
    if 'customer' in keys and 'businessPartner' in keys:
        return 'Customer'
    if 'product' in keys and 'mrpType' in keys:
        return 'Product'
    return 'Unknown'


def load_data(pdf_path: str) -> dict:
    """Parse PDF and load all entities into SQLite. Returns stats."""
    objects = extract_json_objects_from_pdf(pdf_path)

    stats = {
        "SalesOrder": 0, "SalesOrderItem": 0, "DeliveryHeader": 0,
        "DeliveryItem": 0, "BillingHeader": 0, "BillingItem": 0,
        "JournalEntry": 0, "Customer": 0, "Product": 0,
        "ScheduleLine": 0, "Unknown": 0, "Errors": 0
    }

    conn = get_connection()
    cur = conn.cursor()
    
    # Temporarily disable foreign key checks during bulk insert
    cur.execute("PRAGMA foreign_keys = OFF")
    conn.commit()

    for obj in objects:
        kind = classify_object(obj)
        try:
            if kind == 'Customer':
                cur.execute("""
                    INSERT OR IGNORE INTO customers
                    (customer_id, full_name, grouping, category, language, created_by, creation_date)
                    VALUES (?,?,?,?,?,?,?)
                """, (
                    obj.get('customer') or obj.get('businessPartner'),
                    obj.get('businessPartnerFullName', ''),
                    obj.get('businessPartnerGrouping', ''),
                    obj.get('businessPartnerCategory', ''),
                    obj.get('correspondenceLanguage', ''),
                    obj.get('createdByUser', ''),
                    obj.get('creationDate', ''),
                ))

            elif kind == 'SalesOrder':
                cur.execute("""
                    INSERT OR IGNORE INTO sales_orders
                    (sales_order, order_type, sales_org, dist_channel, division,
                     sold_to_party, creation_date, created_by, total_net_amount,
                     currency, delivery_status, billing_status, total_credit_check_status,
                     pricing_date, requested_delivery, payment_terms, incoterms, incoterms_location)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    obj.get('salesOrder'),
                    obj.get('salesOrderType', ''),
                    obj.get('salesOrganization', ''),
                    obj.get('distributionChannel', ''),
                    obj.get('organizationDivision', ''),
                    obj.get('soldToParty'),
                    obj.get('creationDate'),
                    obj.get('createdByUser', ''),
                    _parse_float(obj.get('totalNetAmount')),
                    obj.get('transactionCurrency', 'INR'),
                    obj.get('overallDeliveryStatus', ''),
                    obj.get('overallOrdReltdBillgStatus', ''),
                    obj.get('totalCreditCheckStatus', ''),
                    obj.get('pricingDate'),
                    obj.get('requestedDeliveryDate'),
                    obj.get('customerPaymentTerms', ''),
                    obj.get('incotermsClassification', ''),
                    obj.get('incotermsLocation1', ''),
                ))

            elif kind == 'SalesOrderItem':
                cur.execute("""
                    INSERT OR IGNORE INTO sales_order_items
                    (sales_order, sales_order_item, item_category, material,
                     requested_quantity, quantity_unit, net_amount, currency,
                     material_group, production_plant, storage_location, billing_block)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    obj.get('salesOrder'),
                    obj.get('salesOrderItem'),
                    obj.get('salesOrderItemCategory', ''),
                    obj.get('material', ''),
                    _parse_float(obj.get('requestedQuantity')),
                    obj.get('requestedQuantityUnit', ''),
                    _parse_float(obj.get('netAmount')),
                    obj.get('transactionCurrency', 'INR'),
                    obj.get('materialGroup', ''),
                    obj.get('productionPlant', ''),
                    obj.get('storageLocation', ''),
                    obj.get('itemBillingBlockReason', ''),
                ))

            elif kind == 'DeliveryHeader':
                cur.execute("""
                    INSERT OR IGNORE INTO delivery_headers
                    (delivery_document, shipping_point, overall_goods_mvt,
                     overall_picking, overall_pod, goods_mvt_date, creation_date,
                     delivery_block, billing_block)
                    VALUES (?,?,?,?,?,?,?,?,?)
                """, (
                    obj.get('deliveryDocument'),
                    obj.get('shippingPoint', ''),
                    obj.get('overallGoodsMovementStatus', ''),
                    obj.get('overallPickingStatus', ''),
                    obj.get('overallProofOfDeliveryStatus', ''),
                    obj.get('actualGoodsMovementDate'),
                    obj.get('creationDate'),
                    obj.get('deliveryBlockReason', ''),
                    obj.get('headerBillingBlockReason', ''),
                ))

            elif kind == 'DeliveryItem':
                cur.execute("""
                    INSERT OR IGNORE INTO delivery_items
                    (delivery_document, delivery_item, plant, storage_location,
                     material, actual_qty, qty_unit, ref_sales_order,
                     ref_sales_order_item, last_change_date)
                    VALUES (?,?,?,?,?,?,?,?,?,?)
                """, (
                    obj.get('deliveryDocument'),
                    obj.get('deliveryDocumentItem'),
                    obj.get('plant', ''),
                    obj.get('storageLocation', ''),
                    obj.get('material', ''),
                    _parse_float(obj.get('actualDeliveryQuantity')),
                    obj.get('deliveryQuantityUnit', ''),
                    obj.get('referenceSdDocument'),
                    obj.get('referenceSdDocumentItem'),
                    obj.get('lastChangeDate'),
                ))

            elif kind == 'BillingHeader':
                ct = obj.get('creationTime', {})
                cur.execute("""
                    INSERT OR IGNORE INTO billing_headers
                    (billing_document, billing_type, billing_date, creation_date,
                     is_cancelled, cancelled_doc, total_net_amount, currency,
                     company_code, fiscal_year, accounting_document, sold_to_party)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    obj.get('billingDocument'),
                    obj.get('billingDocumentType', ''),
                    obj.get('billingDocumentDate'),
                    obj.get('creationDate'),
                    _parse_bool(obj.get('billingDocumentIsCancelled', False)),
                    obj.get('cancelledBillingDocument', ''),
                    _parse_float(obj.get('totalNetAmount')),
                    obj.get('transactionCurrency', 'INR'),
                    obj.get('companyCode', ''),
                    obj.get('fiscalYear', ''),
                    obj.get('accountingDocument', ''),
                    obj.get('soldToParty', ''),
                ))

            elif kind == 'BillingItem':
                cur.execute("""
                    INSERT OR IGNORE INTO billing_items
                    (billing_document, billing_item, material, billing_quantity,
                     qty_unit, net_amount, currency, ref_sales_order, ref_sales_order_item)
                    VALUES (?,?,?,?,?,?,?,?,?)
                """, (
                    obj.get('billingDocument'),
                    obj.get('billingDocumentItem'),
                    obj.get('material', ''),
                    _parse_float(obj.get('billingQuantity')),
                    obj.get('billingQuantityUnit', ''),
                    _parse_float(obj.get('netAmount')),
                    obj.get('transactionCurrency', 'INR'),
                    obj.get('referenceSdDocument'),
                    obj.get('referenceSdDocumentItem'),
                ))

            elif kind == 'JournalEntry':
                cur.execute("""
                    INSERT OR IGNORE INTO journal_entries
                    (company_code, fiscal_year, accounting_document, accounting_doc_item,
                     gl_account, reference_document, cost_center, profit_center,
                     currency, amount_in_currency, company_currency, amount_in_company_currency,
                     posting_date, document_date, doc_type, assignment_ref,
                     customer, financial_account_type, clearing_date, clearing_doc)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    obj.get('companyCode', ''),
                    obj.get('fiscalYear', ''),
                    obj.get('accountingDocument'),
                    obj.get('accountingDocumentItem'),
                    obj.get('glAccount', ''),
                    obj.get('referenceDocument', ''),
                    obj.get('costCenter', ''),
                    obj.get('profitCenter', ''),
                    obj.get('transactionCurrency', 'INR'),
                    _parse_float(obj.get('amountInTransactionCurrency')),
                    obj.get('companyCodeCurrency', 'INR'),
                    _parse_float(obj.get('amountInCompanyCodeCurrency')),
                    obj.get('postingDate'),
                    obj.get('documentDate'),
                    obj.get('accountingDocumentType', ''),
                    obj.get('assignmentReference', ''),
                    obj.get('customer', ''),
                    obj.get('financialAccountType', ''),
                    obj.get('clearingDate'),
                    obj.get('clearingAccountingDocument', ''),
                ))

            elif kind == 'Product':
                cur.execute("""
                    INSERT OR IGNORE INTO products
                    (product, plant, profit_center, mrp_type, country_origin)
                    VALUES (?,?,?,?,?)
                """, (
                    obj.get('product'),
                    obj.get('plant', ''),
                    obj.get('profitCenter', ''),
                    obj.get('mrpType', ''),
                    obj.get('countryOfOrigin', ''),
                ))

            elif kind == 'ScheduleLine':
                pass  # Skip schedule lines for now

            else:
                stats['Unknown'] += 1
                continue

            stats[kind] += 1

        except Exception as e:
            stats['Errors'] += 1
            if kind in ['BillingItem', 'JournalEntry']:
                print(f"  ERROR inserting {kind}: {str(e)}")
                print(f"    Object keys: {list(obj.keys())}")

    # Re-enable foreign key checks
    cur.execute("PRAGMA foreign_keys = ON")
    conn.commit()
    conn.close()

    print("\n[DataProcessor] Load complete:")
    for k, v in stats.items():
        if v > 0:
            print(f"  {k}: {v}")

    return stats


def is_data_loaded() -> bool:
    """Check if data has already been loaded."""
    try:
        conn = get_connection()
        cur = conn.execute("SELECT COUNT(*) as cnt FROM sales_orders")
        row = cur.fetchone()
        conn.close()
        return row['cnt'] > 0
    except Exception:
        return False
