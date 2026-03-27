"""
llm_service.py – Groq-powered natural language query engine.
Handles: model selection, guardrails, NL→SQL translation, RAG response generation.
"""
import os
import re
import json
import requests
from database import execute_query, get_schema

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_BASE_URL = "https://api.groq.com/openai/v1"

# Domain keywords that indicate a valid business query
DOMAIN_KEYWORDS = [
    "order", "delivery", "invoice", "billing", "payment", "customer",
    "product", "material", "journal", "accounting", "sales", "amount",
    "quantity", "date", "status", "flow", "document", "entry", "plant",
    "gl", "account", "fiscal", "currency", "inr", "company", "profit",
    "cost", "center", "shipped", "dispatched", "billed", "complete",
    "incomplete", "broken", "cancelled", "revenue", "vendor", "supplier",
    "trace", "track", "find", "show", "list", "which", "how many", "what",
    "identify", "analyze", "summarize", "count", "total", "top", "highest",
    "lowest", "average", "pending", "outstanding", "cleared", "open",
    "closed", "sold", "dispatch", "shipment", "goods", "movement",
    "party", "partner", "740", "905", "310", "320",  # typical ID prefixes
]

SYSTEM_PROMPT = """You are a specialized Graph AI assistant for an Order-to-Cash (O2C) business process system.
You have access to a dataset containing Sales Orders, Deliveries, Billing Documents, Journal Entries, Customers, and Products.

Your ONLY purpose is to answer questions about this dataset. You must:
1. Only answer questions related to the O2C business process and the dataset
2. Translate natural language questions into SQL queries
3. Return data-backed answers based on query results
4. NEVER make up data or answer from memory — always use the SQL query results

GUARDRAILS — If a question is NOT about the dataset or O2C process, respond EXACTLY with:
"This system is designed to answer questions related to the provided Order-to-Cash dataset only. Please ask questions about sales orders, deliveries, billing documents, journal entries, customers, or products."

{schema}

INSTRUCTIONS FOR SQL GENERATION:
- Generate valid SQLite SQL
- Use JOINs to connect related tables
- Always use table aliases for clarity
- Limit results to 50 rows unless user asks for more
- For date comparisons, use standard ISO format: '2025-04-02'
- Return the SQL query in a JSON block: {{"sql": "SELECT ...", "explanation": "..."}}
- After the JSON block, provide the natural language response template

EXAMPLE FLOW:
User: "Which products are associated with the highest number of billing documents?"
Response:
{{"sql": "SELECT bi.material, COUNT(DISTINCT bi.billing_document) as billing_count FROM billing_items bi GROUP BY bi.material ORDER BY billing_count DESC LIMIT 10", "explanation": "Count distinct billing documents per material"}}
ANSWER_TEMPLATE: The products with the highest number of billing documents are: {{results}}

User: "Trace the full flow of billing document 90504298"
Response:
{{"sql": "SELECT so.sales_order, dh.delivery_document, bh.billing_document, je.accounting_document FROM billing_headers bh LEFT JOIN billing_items bi ON bi.billing_document = bh.billing_document LEFT JOIN sales_orders so ON so.sales_order = bi.ref_sales_order LEFT JOIN delivery_items di ON di.ref_sales_order = so.sales_order LEFT JOIN delivery_headers dh ON dh.delivery_document = di.delivery_document LEFT JOIN journal_entries je ON je.reference_document = bh.billing_document WHERE bh.billing_document = '90504298' LIMIT 10", "explanation": "Full O2C flow trace for billing document"}}
ANSWER_TEMPLATE: Here is the complete flow for billing document 90504298: {{results}}
"""


def get_available_groq_model() -> str:
    """Dynamically fetch the best available Groq text model."""
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    try:
        response = requests.get(f"{GROQ_BASE_URL}/models", headers=headers, timeout=10)
        response.raise_for_status()
        models = response.json().get("data", [])

        # Filter out non-text models
        valid_models = []
        for m in models:
            model_id = m["id"]
            if any(x in model_id.lower() for x in ["audio", "tts", "speech", "whisper", "orpheus", "vision"]):
                continue
            # Prefer llama3 or gemma models
            valid_models.append(model_id)

        # Prefer specific models
        preferred = ["llama-3.3-70b-versatile", "llama3-70b-8192", "llama3-8b-8192",
                     "mixtral-8x7b-32768", "gemma2-9b-it"]
        for pref in preferred:
            for m in valid_models:
                if pref in m:
                    print(f"[LLM] Using model: {m}")
                    return m

        if valid_models:
            print(f"[LLM] Using model: {valid_models[0]}")
            return valid_models[0]

    except Exception as e:
        print(f"[LLM] Could not fetch models: {e}")

    return "llama3-8b-8192"  # fallback


# Cache the model name
_cached_model = None


def get_model() -> str:
    global _cached_model
    if not _cached_model:
        _cached_model = get_available_groq_model()
    return _cached_model


def is_domain_query(query: str) -> bool:
    """
    Guardrail: check if the query is related to the O2C domain.
    Returns True if the query is relevant, False otherwise.
    """
    q_lower = query.lower()

    # Obvious off-topic patterns
    off_topic_patterns = [
        r'\b(write|compose|create|generate)\s+(a\s+)?(poem|story|essay|song|joke|recipe)\b',
        r'\b(who|what)\s+is\s+(the\s+)?(president|prime minister|king|queen|ceo of google|ceo of apple)\b',
        r'\b(weather|temperature|forecast)\b',
        r'\b(translate|translation)\s+to\s+\w+\b',
        r'\bhow\s+to\s+(cook|bake|make|draw|paint)\b',
        r'\b(capital\s+of|largest\s+country|tallest\s+building)\b',
        r'\b(sports|cricket|football|movie|film|actor|actress)\b',
        r'\b(calculate|solve)\s+\d+\s*[\+\-\*\/]\s*\d+\b',
    ]

    for pattern in off_topic_patterns:
        if re.search(pattern, q_lower):
            return False

    # Check for domain keywords
    for kw in DOMAIN_KEYWORDS:
        if kw in q_lower:
            return True

    # Very short queries are ambiguous — allow them
    if len(q_lower.split()) <= 4:
        return True

    return False


def extract_sql_from_response(text: str) -> tuple[str | None, str | None]:
    """Extract SQL and explanation from LLM response."""
    # Try to find JSON block
    json_pattern = r'\{[^{}]*"sql"[^{}]*\}'
    match = re.search(json_pattern, text, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group())
            return data.get('sql'), data.get('explanation')
        except json.JSONDecodeError:
            pass

    # Try code block
    sql_block = re.search(r'```sql\s*(.*?)\s*```', text, re.DOTALL | re.IGNORECASE)
    if sql_block:
        return sql_block.group(1).strip(), None

    # Try to find SELECT statement directly
    select_match = re.search(r'(SELECT\s+.*?(?:;|$))', text, re.DOTALL | re.IGNORECASE)
    if select_match:
        return select_match.group(1).strip(), None

    return None, None


def format_results_for_llm(results: list[dict]) -> str:
    """Format query results as a readable string for LLM."""
    if not results:
        return "No results found."
    if len(results) == 1:
        return "\n".join(f"  {k}: {v}" for k, v in results[0].items() if v is not None)

    # Tabular format for multiple results
    if len(results) <= 20:
        lines = []
        headers = list(results[0].keys())
        lines.append(" | ".join(str(h) for h in headers))
        lines.append("-" * 80)
        for row in results:
            lines.append(" | ".join(str(row.get(h, '')) for h in headers))
        return "\n".join(lines)
    else:
        # Summary for large result sets
        return f"Found {len(results)} records. First 5:\n" + "\n".join(
            str(r) for r in results[:5]
        )


def _try_fast_query(user_question: str) -> dict | None:
    """
    Fast-track common query patterns WITHOUT calling LLM.
    Returns None if pattern not matched -> falls back to LLM.
    """
    q_lower = user_question.lower()
    
    # Pattern: Broken/incomplete flows
    if any(x in q_lower for x in ["broken", "incomplete", "not billed", "not delivered", "unmatched"]):
        sql = """
        SELECT DISTINCT so.sales_order, so.sold_to_party, so.total_net_amount, so.currency,
               CASE WHEN COUNT(DISTINCT di.delivery_document) = 0 THEN 'No Delivery'
                    WHEN COUNT(DISTINCT bh.billing_document) = 0 THEN 'Delivered but Not Billed'
                    WHEN COUNT(DISTINCT je.accounting_document) = 0 THEN 'Billed but Not Journalized'
                    ELSE 'Complete' END as flow_status
        FROM sales_orders so
        LEFT JOIN sales_order_items soi ON soi.sales_order = so.sales_order
        LEFT JOIN delivery_items di ON di.ref_sales_order = so.sales_order
        LEFT JOIN billing_items bi ON bi.ref_sales_order = so.sales_order
        LEFT JOIN billing_headers bh ON bh.billing_document = bi.billing_document
        LEFT JOIN journal_entries je ON je.reference_document = bh.billing_document
        GROUP BY so.sales_order
        HAVING flow_status IN ('No Delivery', 'Delivered but Not Billed', 'Billed but Not Journalized')
        LIMIT 50
        """
        try:
            results = execute_query(sql)
            if len(results) > 0:
                return {
                    "answer": f"Found {len(results)} sales orders with incomplete flows: {', '.join([r['sales_order'] for r in results[:10]])}. These orders have missing stages in the Order-to-Cash process.",
                    "sql": sql,
                    "results": results,
                    "nodes_referenced": [f"SO_{r['sales_order']}" for r in results[:5]]
                }
        except:
            pass
    
    # Pattern: Top products by billing
    if any(x in q_lower for x in ["top", "highest", "most", "billing", "products"]):
        if "product" in q_lower and "bill" in q_lower:
            sql = """
            SELECT bi.material, COUNT(DISTINCT bi.billing_document) as billing_count,
                   SUM(bi.net_amount) as total_billed, bi.currency
            FROM billing_items bi
            GROUP BY bi.material
            ORDER BY billing_count DESC
            LIMIT 20
            """
            try:
                results = execute_query(sql)
                if len(results) > 0:
                    node_refs = [f"PROD_{r['material']}" for r in results[:10]]
                    print(f"[DEBUG] Top products query matched. Returning nodes: {node_refs}")
                    return {
                        "answer": f"Top products by billing documents: {results[0]['material']} ({results[0]['billing_count']} documents, {results[0]['total_billed']} {results[0]['currency']})",
                        "sql": sql,
                        "results": results,
                        "nodes_referenced": node_refs
                    }
            except Exception as e:
                print(f"[ERROR] Top products query failed: {str(e)}")
                import traceback
                traceback.print_exc()
    
    # Pattern: Recent deliveries
    if any(x in q_lower for x in ["recent", "latest", "new", "last"]) and "delivery" in q_lower:
        sql = """
        SELECT dh.delivery_document, dh.goods_mvt_date, dh.shipping_point,
               COUNT(di.delivery_item) as item_count, SUM(di.actual_qty) as total_qty
        FROM delivery_headers dh
        LEFT JOIN delivery_items di ON di.delivery_document = dh.delivery_document
        WHERE dh.goods_mvt_date IS NOT NULL
        GROUP BY dh.delivery_document
        ORDER BY dh.goods_mvt_date DESC
        LIMIT 20
        """
        try:
            results = execute_query(sql)
            if len(results) > 0:
                return {
                    "answer": f"Recent deliveries (latest {len(results)}): {results[0]['delivery_document']} on {results[0]['goods_mvt_date']}",
                    "sql": sql,
                    "results": results,
                    "nodes_referenced": [f"DEL_{r['delivery_document']}" for r in results[:5]]
                }
        except:
            pass
    
    # Pattern: Missing status fields (overallOrdReltdBillgStatus or totalCreditCheckStatus)
    if any(x in q_lower for x in ["missing", "empty", "blank", "null"]) and any(x in q_lower for x in ["status", "billing", "credit", "field"]):
        sql = """
        SELECT so.sales_order, so.sold_to_party, so.order_type, so.delivery_status,
               so.billing_status as overallOrdReltdBillgStatus, 
               so.total_credit_check_status as totalCreditCheckStatus
        FROM sales_orders so
        WHERE (so.billing_status IS NULL OR so.billing_status = '')
           OR (so.total_credit_check_status IS NULL OR so.total_credit_check_status = '')
        LIMIT 50
        """
        try:
            results = execute_query(sql)
            missing_billing = len([r for r in results if r['overallOrdReltdBillgStatus'] is None or r['overallOrdReltdBillgStatus'] == ''])
            missing_credit = len([r for r in results if r['totalCreditCheckStatus'] is None or r['totalCreditCheckStatus'] == ''])
            
            if len(results) > 0:
                answer = f"Found {len(results)} orders with missing status fields: "
                if missing_billing > 0:
                    answer += f"{missing_billing} with missing overallOrdReltdBillgStatus; "
                if missing_credit > 0:
                    answer += f"{missing_credit} with missing totalCreditCheckStatus."
                
                return {
                    "answer": answer,
                    "sql": sql,
                    "results": results,
                    "nodes_referenced": [f"SO_{r['sales_order']}" for r in results[:10]]
                }
            else:
                return {
                    "answer": "No records found with missing overallOrdReltdBillgStatus or totalCreditCheckStatus. All records have these status fields populated.",
                    "sql": sql,
                    "results": [],
                    "nodes_referenced": []
                }
        except Exception as e:
            pass
    
    # Pattern: Find linked records by document number (e.g., "91150187 - find journal entry")
    import re as re_module
    doc_match = re_module.search(r'\b(\d{7,10})\b', q_lower)
    if doc_match and any(x in q_lower for x in ["link", "linked", "find", "connect", "journal", "billing", "relate"]):
        doc_number = doc_match.group(1)
        
        # Try to find as billing document - check if it has an accounting_document field that links to journal entry
        sql = """
        SELECT bh.billing_document, bh.accounting_document, je.accounting_document, je.company_code, je.gl_account,
               je.currency, je.amount_in_currency
        FROM billing_headers bh
        LEFT JOIN journal_entries je ON je.accounting_document = bh.accounting_document
        WHERE bh.billing_document = ?
        LIMIT 10
        """
        try:
            results = execute_query(sql, (doc_number,))
            if len(results) > 0 and results[0].get('accounting_document'):
                je_num = results[0]['accounting_document']
                return {
                    "answer": f"The journal entry number linked to {doc_number} is {je_num}. This value is found in the accounting_document column. According to the data, there is a unique link between the billing document {doc_number} and the journal entry {je_num}.",
                    "sql": sql.replace('?', f"'{doc_number}'"),
                    "results": results,
                    "nodes_referenced": [f"BILL_{doc_number}", f"JE_{je_num}_1"]
                }
            else:
                # Try as sales order
                sql2 = """
                SELECT so.sales_order, bh.billing_document, bh.accounting_document, je.accounting_document
                FROM sales_orders so
                LEFT JOIN billing_items bi ON bi.ref_sales_order = so.sales_order
                LEFT JOIN billing_headers bh ON bh.billing_document = bi.billing_document
                LEFT JOIN journal_entries je ON je.accounting_document = bh.accounting_document
                WHERE so.sales_order = ?
                LIMIT 10
                """
                results2 = execute_query(sql2, (doc_number,))
                if len(results2) > 0:
                    billing_doc = results2[0].get('billing_document', '')
                    je_doc = results2[0].get('accounting_document', '')
                    node_refs = [f"SO_{doc_number}"]
                    if billing_doc:
                        node_refs.append(f"BILL_{billing_doc}")
                    if je_doc:
                        node_refs.append(f"JE_{je_doc}_1")
                    return {
                        "answer": f"Found linked records for order {doc_number}: Billing document {billing_doc or 'N/A'}, Journal entry {je_doc or 'N/A'}.",
                        "sql": sql2.replace('?', f"'{doc_number}'"),
                        "results": results2,
                        "nodes_referenced": node_refs
                    }
                else:
                    # Document not found in either table
                    return {
                        "answer": f"Document {doc_number} not found in the system. Please verify the document number.",
                        "sql": sql2.replace('?', f"'{doc_number}'"),
                        "results": [],
                        "nodes_referenced": []
                    }
        except Exception as e:
            pass
    
    return None  # Fall back to LLM


def query(user_question: str, conversation_history: list = None) -> dict:
    """
    Main entry point: NL query → SQL → data → NL response.
    Returns: {"answer": str, "sql": str|None, "results": list, "nodes_referenced": list}
    """
    if not GROQ_API_KEY or GROQ_API_KEY == "your_groq_api_key_here":
        return {
            "answer": "⚠️ GROQ_API_KEY is not configured. Please set it in your .env file.",
            "sql": None,
            "results": [],
            "nodes_referenced": []
        }

    # Guardrail check
    if not is_domain_query(user_question):
        return {
            "answer": "This system is designed to answer questions related to the provided Order-to-Cash dataset only. Please ask questions about sales orders, deliveries, billing documents, journal entries, customers, or products.",
            "sql": None,
            "results": [],
            "nodes_referenced": []
        }

    # Try fast-track queries first (no LLM call)
    fast_result = _try_fast_query(user_question)
    if fast_result:
        return fast_result

    model = get_model()
    schema = get_schema()

    # Build messages
    system_content = SYSTEM_PROMPT.format(schema=schema)
    messages = [{"role": "system", "content": system_content}]

    # Add conversation history (last 4 turns for context)
    if conversation_history:
        for msg in conversation_history[-8:]:
            messages.append(msg)

    messages.append({"role": "user", "content": user_question})

    # --- First call: generate SQL ---
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        resp = requests.post(
            f"{GROQ_BASE_URL}/chat/completions",
            headers=headers,
            json={
                "model": model,
                "messages": messages,
                "temperature": 0.1,
                "max_tokens": 1024,
            },
            timeout=30
        )
        resp.raise_for_status()
        llm_text = resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return {
            "answer": f"Error calling Groq API: {str(e)}",
            "sql": None,
            "results": [],
            "nodes_referenced": []
        }

    # Extract SQL
    sql, explanation = extract_sql_from_response(llm_text)

    results = []
    sql_error = None
    nodes_referenced = []

    if sql:
        # Sanitize: only allow SELECT
        clean_sql = sql.strip().rstrip(';')
        if not clean_sql.upper().startswith("SELECT"):
            sql_error = "Only SELECT queries are allowed."
        else:
            try:
                results = execute_query(clean_sql)
                # Extract node IDs for highlighting
                nodes_referenced = _extract_node_refs(results)
            except Exception as e:
                sql_error = str(e)
                # Try a fallback query
                results = []

    # --- Second call: generate natural language answer ---
    result_text = format_results_for_llm(results)

    answer_prompt = f"""Based on the following SQL query results, answer the user's question in clear, concise natural language.
Be specific and cite the actual data values. If there are no results, explain what that means.

User question: {user_question}
SQL used: {sql or 'N/A'}
{f'SQL Error: {sql_error}' if sql_error else ''}
Query results:
{result_text}

Provide a clear, data-backed answer in 2-4 sentences. Start directly with the answer, no preamble."""

    try:
        resp2 = requests.post(
            f"{GROQ_BASE_URL}/chat/completions",
            headers=headers,
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": "You are a business data analyst. Answer concisely using only the provided query results."},
                    {"role": "user", "content": answer_prompt}
                ],
                "temperature": 0.2,
                "max_tokens": 512,
            },
            timeout=30
        )
        resp2.raise_for_status()
        final_answer = resp2.json()["choices"][0]["message"]["content"]
    except Exception as e:
        final_answer = result_text if results else f"Query executed but could not generate answer: {str(e)}"

    return {
        "answer": final_answer,
        "sql": sql,
        "results": results[:50],  # cap at 50 rows
        "nodes_referenced": nodes_referenced,
        "sql_error": sql_error,
    }


def _extract_node_refs(results: list[dict]) -> list[str]:
    """Extract node IDs from query results for graph highlighting.
    Works for ANY query result - extracts entities from known column patterns.
    """
    node_ids = []
    for row in results:
        for key, val in row.items():
            if not val:
                continue
            val_str = str(val).strip()
            if not val_str or val_str == "None":
                continue
            
            key_lower = key.lower()
            
            # Billing document
            if 'billing_document' in key_lower or 'billing_doc' in key_lower:
                node_ids.append(f"BILL_{val_str}")
            # Sales order
            elif 'sales_order' in key_lower and 'item' not in key_lower:
                node_ids.append(f"SO_{val_str}")
            # Delivery document
            elif 'delivery_document' in key_lower or 'delivery_doc' in key_lower:
                node_ids.append(f"DEL_{val_str}")
            # Journal entry - use accounting_document with item number
            elif 'accounting_document' in key_lower:
                # If we have accounting_doc_item, use it; otherwise default to 1
                node_ids.append(f"JE_{val_str}_1")
            # Customer
            elif any(x in key_lower for x in ['customer_id', 'sold_to_party', 'cust', 'customer']):
                node_ids.append(f"CUST_{val_str}")
            # Product
            elif any(x in key_lower for x in ['material', 'product_id', 'product']):
                node_ids.append(f"PROD_{val_str}")
    
    # Deduplicate and return
    return list(set(node_ids))
