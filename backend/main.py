"""
main.py – FastAPI application for the Order-to-Cash Graph Query System.
Endpoints:
  GET  /api/graph        – Full graph JSON for D3.js visualization
  POST /api/query        – Natural language query endpoint
  GET  /api/node/{id}    – Get single node details
  GET  /api/stats        – Dataset statistics
  GET  /api/health       – Health check
  POST /api/reload       – Reload data from PDF
"""
import os
import sys
from pathlib import Path
from contextlib import asynccontextmanager
import asyncio

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

# Adjust path for imports
sys.path.insert(0, str(Path(__file__).parent))

import database
import data_processor
import graph_builder
import llm_service


# ── Startup ─────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[Startup] Initializing Order-to-Cash Graph System...")
    database.init_db()

    pdf_path = os.getenv("PDF_PATH", "./data/final_full_dataset.pdf")
    
    # Always attempt to load data if database is empty
    if not data_processor.is_data_loaded():
        if Path(pdf_path).exists():
            print(f"[Startup] Loading data from {pdf_path}...")
            try:
                data_processor.load_data(pdf_path)
                print("[Startup] Data loading complete.")
            except Exception as e:
                print(f"[Startup] ERROR loading data: {e}")
        else:
            print(f"[Startup] WARNING: PDF not found at {pdf_path}. Using empty database.")
    else:
        print("[Startup] Data already loaded.")

    print("[Startup] Building graph...")
    try:
        graph_builder.get_graph()
        print("[Startup] Graph built successfully.")
    except Exception as e:
        print(f"[Startup] ERROR building graph: {e}")
    
    print("[Startup] Ready.")
    yield
    print("[Shutdown] Goodbye.")


app = FastAPI(
    title="Order-to-Cash Graph Query System",
    description="Graph-based data modeling and LLM-powered query interface for O2C processes.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:5500",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5500",
        "http://127.0.0.1:8000",
        "https://*.vercel.app",
        "https://*.netlify.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request/Response Models ──────────────────────────────────────────────────
class QueryRequest(BaseModel):
    question: str
    conversation_history: list = []


class QueryResponse(BaseModel):
    answer: str
    sql: str | None = None
    results: list = []
    nodes_referenced: list = []
    sql_error: str | None = None


# ── API Routes ───────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {"status": "ok", "model": llm_service.get_model()}


@app.get("/api/stats")
async def stats():
    """Return dataset statistics."""
    def count(table: str) -> int:
        try:
            rows = database.execute_query(f"SELECT COUNT(*) as cnt FROM {table}")
            return rows[0]['cnt'] if rows else 0
        except Exception:
            return 0

    G = graph_builder.get_graph()
    return {
        "customers": count("customers"),
        "sales_orders": count("sales_orders"),
        "sales_order_items": count("sales_order_items"),
        "delivery_headers": count("delivery_headers"),
        "delivery_items": count("delivery_items"),
        "billing_headers": count("billing_headers"),
        "billing_items": count("billing_items"),
        "journal_entries": count("journal_entries"),
        "products": count("products"),
        "graph_nodes": G.number_of_nodes(),
        "graph_edges": G.number_of_edges(),
    }


@app.get("/api/graph")
async def get_graph():
    """Return graph data for D3.js visualization."""
    G = graph_builder.get_graph()
    data = graph_builder.graph_to_json(G, max_nodes=700)
    return JSONResponse(content=data)


@app.get("/api/node/{node_id:path}")
async def get_node(node_id: str):
    """Return details for a specific node."""
    G = graph_builder.get_graph()
    if not G.has_node(node_id):
        raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found.")

    data = dict(G.nodes[node_id])
    neighbors = []
    for pred in G.predecessors(node_id):
        neighbors.append({"id": pred, "direction": "in", "relation": G.edges[pred, node_id].get('relation', '')})
    for succ in G.successors(node_id):
        neighbors.append({"id": succ, "direction": "out", "relation": G.edges[node_id, succ].get('relation', '')})

    return {
        "node_id": node_id,
        "type": data.get("type"),
        "label": data.get("label"),
        "metadata": data.get("metadata", {}),
        "connections": len(neighbors),
        "neighbors": neighbors[:20],
    }


@app.post("/api/query", response_model=QueryResponse)
async def query_graph(req: QueryRequest):
    """Process a natural language query and return a data-backed answer."""
    if not req.question or not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    try:
        # Run with 50 second timeout
        result = await asyncio.wait_for(
            asyncio.to_thread(
                llm_service.query,
                req.question.strip(),
                req.conversation_history
            ),
            timeout=50
        )
        return QueryResponse(**result)
    except asyncio.TimeoutError:
        return QueryResponse(
            answer="⚠️ Query processing timed out. The query was too complex. Please try a simpler question or break it into smaller queries.",
            sql=None,
            results=[],
            nodes_referenced=[]
        )


@app.post("/api/reload")
async def reload_data():
    """Reload data from the PDF (drops and recreates all tables)."""
    pdf_path = os.getenv("PDF_PATH", "./data/final_full_dataset.pdf")
    if not Path(pdf_path).exists():
        raise HTTPException(status_code=404, detail=f"PDF not found at {pdf_path}")

    # Drop and recreate
    conn = database.get_connection()
    tables = ["journal_entries", "billing_items", "billing_headers",
              "delivery_items", "delivery_headers", "sales_order_items",
              "sales_orders", "customers", "products"]
    for t in tables:
        conn.execute(f"DELETE FROM {t}")
    conn.commit()
    conn.close()

    stats = data_processor.load_data(pdf_path)
    graph_builder.reset_graph()
    graph_builder.get_graph()

    return {"status": "reloaded", "stats": stats}


# ── Frontend Serving (for local development) ────────────────────────────────
frontend_path = Path(__file__).parent.parent / "frontend"

@app.get("/")
async def root():
    """Serve frontend index.html for local development."""
    index_file = frontend_path / "index.html"
    if index_file.exists():
        return FileResponse(index_file, media_type="text/html")
    
    # Fallback if frontend not found
    return {
        "status": "ok",
        "service": "Order-to-Cash Graph API",
        "version": "1.0.0",
        "docs_url": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)), reload=False)
