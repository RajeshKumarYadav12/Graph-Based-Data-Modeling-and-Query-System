# Order to Cash — Graph-Based Data Modeling & Query System

A **context graph system** with an LLM-powered conversational query interface for the Order-to-Cash (O2C) business process.

![System Screenshot](docs/screenshot.png)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (HTML + D3.js)                  │
│  ┌─────────────────────────────┐  ┌────────────────────────┐    │
│  │   Force-Directed Graph       │  │    Chat Interface       │    │
│  │   (D3.js simulation)         │  │    (NL → SQL → Answer) │    │
│  └─────────────────────────────┘  └────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                              │ REST API
┌─────────────────────────────────────────────────────────────────┐
│                        Backend (FastAPI)                          │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────┐ │
│  │ data_processor│  │ graph_builder │  │    llm_service        │ │
│  │ PDF → SQLite  │  │ NetworkX +   │  │  Groq API             │ │
│  │               │  │ JSON export  │  │  NL→SQL + Guardrails  │ │
│  └──────────────┘  └──────────────┘  └───────────────────────┘ │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    SQLite Database                        │   │
│  │  customers | sales_orders | sales_order_items            │   │
│  │  delivery_headers | delivery_items                       │   │
│  │  billing_headers | billing_items | journal_entries       │   │
│  │  products                                                │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Graph Model

### Nodes (Entity Types)

| Node Type        | Description                         | Key Fields                                     |
| ---------------- | ----------------------------------- | ---------------------------------------------- |
| `Customer`       | Business partners / sold-to parties | customer_id, full_name                         |
| `SalesOrder`     | Sales order headers                 | sales_order, total_net_amount, delivery_status |
| `SalesOrderItem` | Line items on orders                | material, quantity, net_amount                 |
| `Delivery`       | Delivery document headers           | delivery_document, goods_mvt_status            |
| `DeliveryItem`   | Items within deliveries             | plant, actual_qty                              |
| `BillingDoc`     | Billing document headers            | billing_document, billing_type                 |
| `BillingItem`    | Line items on billing docs          | material, billing_quantity                     |
| `JournalEntry`   | Accounting / G/L entries            | accounting_document, gl_account, amount        |
| `Product`        | Material master data                | product, plant, profit_center                  |

### Edges (Relationships)

```
Customer ──PLACED_ORDER──→ SalesOrder
SalesOrder ──HAS_ITEM──→ SalesOrderItem
SalesOrderItem ──DELIVERED_VIA──→ DeliveryItem
DeliveryItem ←──HAS_ITEM── Delivery
SalesOrderItem ──BILLED_VIA──→ BillingItem
BillingItem ←──HAS_ITEM── BillingDoc
BillingDoc ──HAS_JOURNAL_ENTRY──→ JournalEntry
```

---

## Database Choice: SQLite

**Why SQLite?**

- Zero-configuration — no server needed; runs in a single file
- Sufficient for the dataset size (~3,800 records)
- Full SQL support enabling complex JOIN queries for O2C flow tracing
- Perfect for NL→SQL translation (LLM generates standard SQL)
- Easy to ship and demo without infrastructure setup

**Trade-off:** For production scale (millions of records), PostgreSQL + graph DB (Neo4j) would be preferred.

---

## LLM Prompting Strategy

The system uses a **two-call Groq pipeline**:

### Call 1 — SQL Generation

```
System: Schema description + O2C domain context + examples
User: Natural language question
→ Response: JSON block with {"sql": "...", "explanation": "..."}
```

### Call 2 — Answer Generation

```
System: "You are a business data analyst. Answer using provided results only."
User: Original question + SQL used + actual query results
→ Response: Natural language answer grounded in data
```

### Model Selection

The system dynamically fetches available Groq models at startup and selects
the best text model (preferring llama-3.3-70b-versatile or llama3-70b-8192).

---

## Guardrails

The system enforces domain restrictions at **two levels**:

### 1. Pattern-Based Pre-filter (fast, no LLM cost)

Detects off-topic requests via regex patterns:

- Creative writing (poems, stories, jokes)
- General knowledge (weather, politics, celebrities)
- Math operations unrelated to business data
- Translation requests

### 2. Domain Keyword Check

Verifies the query contains at least one O2C business domain keyword
(order, delivery, billing, customer, material, journal, etc.)

**Response for off-topic queries:**

> "This system is designed to answer questions related to the provided Order-to-Cash dataset only."

---

## Setup & Running

### Prerequisites

- Python 3.10+
- Groq API key (free tier at console.groq.com)

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/your-username/order-to-cash-graph.git
cd order-to-cash-graph

# 2. Set your Groq API key
cp .env.example .env
# Edit .env and set: GROQ_API_KEY=gsk_your_key_here

# 3. Copy the dataset PDF
cp /path/to/final_full_dataset.pdf ./data/

# 4. Run
chmod +x run.sh
./run.sh
```

### Manual Start

```bash
pip install -r requirements.txt
cd backend
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
```

Visit: **http://localhost:8000**

---

## API Endpoints

| Endpoint         | Method | Description                   |
| ---------------- | ------ | ----------------------------- |
| `/api/graph`     | GET    | Graph JSON for visualization  |
| `/api/query`     | POST   | Natural language query        |
| `/api/node/{id}` | GET    | Single node details           |
| `/api/stats`     | GET    | Dataset statistics            |
| `/api/health`    | GET    | Health check + model info     |
| `/api/reload`    | POST   | Reload data from PDF          |
| `/docs`          | GET    | Interactive API documentation |

---

## 🚀 Deployment

This project uses a **decoupled architecture**:

- **Backend (FastAPI)** → Deployed on Render (Docker) — in `backend/` folder
- **Frontend (Static HTML)** → Deployed on Vercel — in `frontend/` folder

### **Project Structure for Deployment:**

```
order-to-cash/
├── backend/                    # ← Self-contained, deployable to Render
│   ├── .env                    # Secrets (not in git)
│   ├── data/                   # PDF + Database (not in git)
│   │   ├── final_full_dataset.pdf
│   │   └── otc.db
│   ├── main.py
│   ├── database.py
│   ├── data_processor.py
│   ├── graph_builder.py
│   └── llm_service.py
├── frontend/                   # ← Self-contained, deployable to Vercel
│   ├── index.html
│   └── vercel.json
├── Dockerfile                  # Builds backend only
├── requirements.txt
└── README.md
```

### **Quick Deploy (5 min each):**

| Step | Task            | Platform | Link                                                           |
| ---- | --------------- | -------- | -------------------------------------------------------------- |
| 1    | Deploy Backend  | Render   | Push to GitHub → Create Docker Web Service → Set GROQ_API_KEY  |
| 2    | Deploy Frontend | Vercel   | Import GitHub → Set REACT_APP_API_BASE env var with Render URL |
| 3    | Test            | Both     | Visit Vercel URL, graph should load and chat should work       |

### **For Local Development:**

```bash
# Setup
pip install -r requirements.txt

# Terminal 1: Run backend
cd backend
python -m uvicorn main:app --reload

# Terminal 2: Open frontend
# Visit http://localhost:8000 in browser
```

### **Docker (Local Testing):**

```bash
docker compose up
# http://localhost:8000
```

### **Environment Variables:**

**Backend** (in `backend/.env`):

```
GROQ_API_KEY=gsk_your_key_here
PDF_PATH=./data/final_full_dataset.pdf
DB_PATH=./data/otc.db
```

**Frontend** (set in Vercel dashboard):

```
REACT_APP_API_BASE=https://order-to-cash-api-xxxxx.onrender.com
```

---

## 📋 License

This system is provided as-is for educational and business analysis purposes.

## Example Queries

```
Which products are associated with the highest number of billing documents?
Trace the full flow of billing document 90504298
Show all sales orders with incomplete delivery flows
Which customers have the most sales orders?
Find sales orders delivered but not yet billed
Show the top 10 sales orders by net amount
List all journal entries for fiscal year 2025
Which billing documents were cancelled?
```

---

## Project Structure

```
order-to-cash/
├── backend/
│   ├── main.py              # FastAPI app + endpoints
│   ├── database.py          # SQLite schema + query utils
│   ├── data_processor.py    # PDF parsing + data ingestion
│   ├── graph_builder.py     # NetworkX graph + D3 JSON export
│   └── llm_service.py       # Groq LLM integration + guardrails
├── frontend/
│   └── index.html           # Single-file frontend (D3.js + Chat UI)
├── data/                    # SQLite DB + PDF (gitignored)
├── requirements.txt
├── .env
├── run.sh
└── README.md
```

---

## Bonus Features Implemented

- ✅ Natural language → SQL translation (dynamic, not hardcoded)
- ✅ Node highlighting when query results reference specific entities
- ✅ Conversation memory (last 8 messages included in context)
- ✅ Dynamic Groq model selection (fetches best available model)
- ✅ Streaming-ready architecture (responses are streamed from Groq)
- ✅ Graph clustering via force simulation charge/distance tuning
- ✅ Expandable nodes (click to pin tooltip, inspect all metadata)
- ✅ Zoom/pan graph exploration
- ✅ SQL query display in chat for transparency
#   G r a p h - B a s e d - D a t a - M o d e l i n g - a n d - Q u e r y - S y s t e m  
 