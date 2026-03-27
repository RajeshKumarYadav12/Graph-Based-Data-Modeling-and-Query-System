"""
graph_builder.py – Build NetworkX graph from SQLite data and export as JSON
for D3.js force-directed visualization.
"""
import networkx as nx
from database import execute_query

# Node type → color mapping (matches the UI screenshots)
NODE_COLORS = {
    "Customer":       "#3b82f6",   # blue
    "SalesOrder":     "#3b82f6",   # blue
    "SalesOrderItem": "#f87171",   # red/pink
    "Delivery":       "#3b82f6",   # blue
    "DeliveryItem":   "#f87171",   # red/pink
    "BillingDoc":     "#3b82f6",   # blue
    "BillingItem":    "#f87171",   # red/pink
    "JournalEntry":   "#f87171",   # red/pink (leaf node)
    "Product":        "#a78bfa",   # purple
}

NODE_SIZES = {
    "Customer":       10,
    "SalesOrder":     8,
    "SalesOrderItem": 4,
    "Delivery":       8,
    "DeliveryItem":   4,
    "BillingDoc":     8,
    "BillingItem":    4,
    "JournalEntry":   4,
    "Product":        3,
}


def build_graph() -> nx.DiGraph:
    G = nx.DiGraph()

    # ── Customers ──────────────────────────────────────────────────────────
    for row in execute_query("SELECT * FROM customers"):
        nid = f"CUST_{row['customer_id']}"
        G.add_node(nid, type="Customer", label=row['customer_id'],
                   entity="Customer", **{k: (v or "") for k, v in row.items()})

    # ── Sales Orders ───────────────────────────────────────────────────────
    for row in execute_query("SELECT * FROM sales_orders"):
        nid = f"SO_{row['sales_order']}"
        G.add_node(nid, type="SalesOrder", label=row['sales_order'],
                   entity="SalesOrder", **{k: (str(v) if v is not None else "") for k, v in row.items()})
        # Edge: Customer → SalesOrder
        cust_nid = f"CUST_{row['sold_to_party']}"
        if G.has_node(cust_nid):
            G.add_edge(cust_nid, nid, relation="PLACED_ORDER")

    # ── Sales Order Items ──────────────────────────────────────────────────
    for row in execute_query("SELECT * FROM sales_order_items"):
        nid = f"SOI_{row['sales_order']}_{row['sales_order_item']}"
        G.add_node(nid, type="SalesOrderItem", label=f"{row['sales_order']}/{row['sales_order_item']}",
                   entity="SalesOrderItem", **{k: (str(v) if v is not None else "") for k, v in row.items()})
        so_nid = f"SO_{row['sales_order']}"
        if G.has_node(so_nid):
            G.add_edge(so_nid, nid, relation="HAS_ITEM")

    # ── Delivery Headers ───────────────────────────────────────────────────
    for row in execute_query("SELECT * FROM delivery_headers"):
        nid = f"DEL_{row['delivery_document']}"
        G.add_node(nid, type="Delivery", label=row['delivery_document'],
                   entity="Delivery", **{k: (str(v) if v is not None else "") for k, v in row.items()})

    # ── Delivery Items ─────────────────────────────────────────────────────
    for row in execute_query("SELECT * FROM delivery_items"):
        nid = f"DELI_{row['delivery_document']}_{row['delivery_item']}"
        G.add_node(nid, type="DeliveryItem", label=f"{row['delivery_document']}/{row['delivery_item']}",
                   entity="DeliveryItem", **{k: (str(v) if v is not None else "") for k, v in row.items()})
        del_nid = f"DEL_{row['delivery_document']}"
        if G.has_node(del_nid):
            G.add_edge(del_nid, nid, relation="HAS_ITEM")
        # DeliveryItem → SalesOrderItem
        soi_nid = f"SOI_{row['ref_sales_order']}_{row['ref_sales_order_item']}"
        if G.has_node(soi_nid):
            G.add_edge(soi_nid, nid, relation="DELIVERED_VIA")

    # ── Billing Document Headers ───────────────────────────────────────────
    for row in execute_query("SELECT * FROM billing_headers"):
        nid = f"BILL_{row['billing_document']}"
        G.add_node(nid, type="BillingDoc", label=row['billing_document'],
                   entity="BillingDoc", **{k: (str(v) if v is not None else "") for k, v in row.items()})

    # ── Billing Document Items ─────────────────────────────────────────────
    for row in execute_query("SELECT * FROM billing_items"):
        nid = f"BILLI_{row['billing_document']}_{row['billing_item']}"
        G.add_node(nid, type="BillingItem", label=f"{row['billing_document']}/{row['billing_item']}",
                   entity="BillingItem", **{k: (str(v) if v is not None else "") for k, v in row.items()})
        bill_nid = f"BILL_{row['billing_document']}"
        if G.has_node(bill_nid):
            G.add_edge(bill_nid, nid, relation="HAS_ITEM")
        # BillingItem → SalesOrderItem
        soi_nid = f"SOI_{row['ref_sales_order']}_{row['ref_sales_order_item']}"
        if G.has_node(soi_nid):
            G.add_edge(soi_nid, nid, relation="BILLED_VIA")

    # ── Journal Entries ────────────────────────────────────────────────────
    for row in execute_query("SELECT * FROM journal_entries"):
        nid = f"JE_{row['accounting_document']}_{row['accounting_doc_item']}"
        G.add_node(nid, type="JournalEntry", label=row['accounting_document'],
                   entity="JournalEntry", **{k: (str(v) if v is not None else "") for k, v in row.items()})
        # JournalEntry → BillingDoc
        bill_nid = f"BILL_{row['reference_document']}"
        if G.has_node(bill_nid):
            G.add_edge(bill_nid, nid, relation="HAS_JOURNAL_ENTRY")

    # ── Products / Materials ───────────────────────────────────────────────
    for row in execute_query("SELECT * FROM products"):
        nid = f"PROD_{row['product']}"
        G.add_node(nid, type="Product", label=row['product'],
                   entity="Product", **{k: (str(v) if v is not None else "") for k, v in row.items()})

    # ── Links: Products to Billing Items ────────────────────────────────────
    for row in execute_query("SELECT DISTINCT material, billing_document, billing_item FROM billing_items"):
        prod_nid = f"PROD_{row['material']}"
        billi_nid = f"BILLI_{row['billing_document']}_{row['billing_item']}"
        if G.has_node(prod_nid) and G.has_node(billi_nid):
            G.add_edge(prod_nid, billi_nid, relation="BILLED_AS")

    # ── Links: Products to Sales Order Items ────────────────────────────────
    for row in execute_query("SELECT DISTINCT material, sales_order, sales_order_item FROM sales_order_items"):
        prod_nid = f"PROD_{row['material']}"
        soi_nid = f"SOI_{row['sales_order']}_{row['sales_order_item']}"
        if G.has_node(prod_nid) and G.has_node(soi_nid):
            G.add_edge(prod_nid, soi_nid, relation="ORDERED_AS")

    return G


def graph_to_json(G: nx.DiGraph, max_nodes: int = 600) -> dict:
    """
    Convert NetworkX graph to D3.js compatible format.
    Samples nodes if graph is too large for visualization.
    """
    all_nodes = list(G.nodes(data=True))

    # Priority sampling: keep major entity nodes, sample minor ones
    priority_types = {"Customer", "SalesOrder", "Delivery", "BillingDoc"}
    minor_types = {"SalesOrderItem", "DeliveryItem", "BillingItem", "JournalEntry", "Product"}

    priority_nodes = [(nid, data) for nid, data in all_nodes if data.get('type') in priority_types]
    minor_nodes = [(nid, data) for nid, data in all_nodes if data.get('type') in minor_types]

    # Sample minor nodes
    import random
    random.seed(42)
    if len(minor_nodes) > max_nodes - len(priority_nodes):
        minor_nodes = random.sample(minor_nodes, max_nodes - len(priority_nodes))

    selected_nodes = priority_nodes + minor_nodes
    selected_ids = {nid for nid, _ in selected_nodes}

    # Build node list
    nodes = []
    node_index = {nid: i for i, (nid, _) in enumerate(selected_nodes)}
    for nid, data in selected_nodes:
        connections = G.degree(nid)
        node_type = data.get('type', 'Unknown')
        nodes.append({
            "id": nid,
            "index": node_index[nid],
            "label": data.get('label', nid),
            "type": node_type,
            "color": NODE_COLORS.get(node_type, "#6b7280"),
            "size": NODE_SIZES.get(node_type, 4),
            "connections": connections,
            "entity": data.get('entity', node_type),
            "metadata": _build_metadata(data),
        })

    # Build edges (only between selected nodes)
    links = []
    for src, tgt, edge_data in G.edges(data=True):
        if src in selected_ids and tgt in selected_ids:
            links.append({
                "source": node_index[src],
                "target": node_index[tgt],
                "relation": edge_data.get('relation', ''),
            })

    return {"nodes": nodes, "links": links}


def _build_metadata(data: dict) -> dict:
    """Build display metadata from node data, excluding internal fields."""
    skip = {'type', 'label', 'entity', 'id', 'metadata'}
    result = {}
    for k, v in data.items():
        if k in skip:
            continue
        if v and v != "None" and v != "":
            # CamelCase the key for display
            display_key = _to_camel_display(k)
            result[display_key] = v
    return result


def _to_camel_display(key: str) -> str:
    """Convert snake_case or camelCase key to readable display label."""
    # Map known keys
    known = {
        'sales_order': 'SalesOrder',
        'sales_order_item': 'SalesOrderItem',
        'sold_to_party': 'SoldToParty',
        'total_net_amount': 'TotalNetAmount',
        'delivery_status': 'DeliveryStatus',
        'billing_status': 'BillingStatus',
        'creation_date': 'CreationDate',
        'delivery_document': 'DeliveryDocument',
        'billing_document': 'BillingDocument',
        'accounting_document': 'AccountingDocument',
        'gl_account': 'GlAccount',
        'reference_document': 'ReferenceDocument',
        'profit_center': 'ProfitCenter',
        'cost_center': 'CostCenter',
        'posting_date': 'PostingDate',
        'document_date': 'DocumentDate',
        'customer_id': 'CustomerID',
        'full_name': 'FullName',
        'billing_type': 'BillingType',
        'fiscal_year': 'FiscalYear',
        'company_code': 'CompanyCode',
        'amount_in_currency': 'AmountInTransactionCurrency',
        'amount_in_company_currency': 'AmountInCompanyCodeCurrency',
        'doc_type': 'AccountingDocumentType',
        'accounting_doc_item': 'AccountingDocumentItem',
        'ref_sales_order': 'ReferenceSdDocument',
        'currency': 'TransactionCurrency',
    }
    if key in known:
        return known[key]
    # Auto-convert snake_case → TitleCase
    return ''.join(word.capitalize() for word in key.split('_'))


# Cached graph
_cached_graph = None


def get_graph() -> nx.DiGraph:
    global _cached_graph
    if _cached_graph is None:
        _cached_graph = build_graph()
    return _cached_graph


def reset_graph():
    global _cached_graph
    _cached_graph = None
