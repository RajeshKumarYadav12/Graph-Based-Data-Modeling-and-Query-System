# 📊 Order-to-Cash Graph System

**Graph-based data modeling & LLM-powered query interface for O2C business processes**

Jokes / stories
Weather / politics
Math queries
Translation 2. Domain Check
Must include keywords:
order, delivery, billing, customer, etc.
Response for Invalid Queries

## Quick Overview

| Aspect         | Details                              |
| -------------- | ------------------------------------ |
| **Framework**  | FastAPI + D3.js + NetworkX           |
| **Database**   | SQLite (auto-initialized)            |
| **LLM**        | Groq API (llama-3.3-70b)             |
| **Deployment** | Render (Backend) + Vercel (Frontend) |

---

## Local Development

### Setup

| Step             | Command                                   |
| ---------------- | ----------------------------------------- |
| 1. Install deps  | `pip install -r requirements.txt`         |
| 2. Set GROQ key  | Create `backend/.env` with `GROQ_API_KEY` |
| 3. Start backend | `cd backend && uvicorn main:app --reload` |
| 4. Open frontend | `http://localhost:8000`                   |

### Environment Variables

| Variable             | Backend     | Frontend | Value                           |
| -------------------- | ----------- | -------- | ------------------------------- |
| `GROQ_API_KEY`       | ✅ Required | ❌       | From console.groq.com           |
| `PDF_PATH`           | ✅ Required | ❌       | `./data/final_full_dataset.pdf` |
| `DB_PATH`            | ✅ Required | ❌       | `./data/otc.db`                 |
| `REACT_APP_API_BASE` | ❌          | ✅ (Dev) | `http://localhost:8000`         |

GROQ_API_KEY
PDF_PATH
DB_PATH

Frontend

| Endpoint         | Method | Purpose                   |
| ---------------- | ------ | ------------------------- |
| `/`              | GET    | Serve frontend HTML       |
| `/api/graph`     | GET    | Full graph JSON for D3.js |
| `/api/stats`     | GET    | Dataset statistics        |
| `/api/query`     | POST   | Natural language query    |
| `/api/node/{id}` | GET    | Single node details       |
| `/api/health`    | GET    | Health check              |
| `/docs`          | GET    | Interactive API docs      |

---

## Data Model

### Node Types

| Type             | Role                          |
| ---------------- | ----------------------------- |
| `Customer`       | Places sales orders           |
| `SalesOrder`     | Has items, delivery status    |
| `SalesOrderItem` | Delivered & billed separately |
| `Delivery`       | Fulfillment document          |
| `DeliveryItem`   | Quantity shipped              |
| `BillingDoc`     | Invoice/Credit memo           |
| `BillingItem`    | Billing line item             |
| `JournalEntry`   | Financial posting             |
| `Product`        | Material master               |

### Relationships

```
Customer →[PLACED_ORDER]→ SalesOrder
SalesOrder →[HAS_ITEM]→ SalesOrderItem
SalesOrderItem →[DELIVERED_VIA]→ DeliveryItem ←[HAS_ITEM]← Delivery
SalesOrderItem →[BILLED_VIA]→ BillingItem ←[HAS_ITEM]← BillingDoc
BillingDoc →[HAS_JOURNAL_ENTRY]→ JournalEntry
```

---

## LLM Pipeline

| Step | Process         | Output           |
| ---- | --------------- | ---------------- |
| 1    | User question   | NL Query         |
| 2    | Groq NL→SQL     | Generated SQL    |
| 3    | Execute Query   | Result rows      |
| 4    | Groq SQL→NL     | Formatted answer |
| 5    | Highlight nodes | Backend response |

**Features:** Domain guardrails, conversation memory (last 8 msgs), dynamic model selection

---

## Deployment

### Backend → Render

| Step | Action                                                           |
| ---- | ---------------------------------------------------------------- |
| 1.   | Create Web Service on Render                                     |
| 2.   | Select Docker runtime                                            |
| 3.   | Set env vars: `GROQ_API_KEY`, `PDF_PATH`, `DB_PATH`              |
| 4.   | Deploy → Get URL: `https://order-to-cash-api-xxxxx.onrender.com` |

### Frontend → Vercel

| Step | Action                                                     |
| ---- | ---------------------------------------------------------- |
| 1.   | Import GitHub repo to Vercel                               |
| 2.   | Root directory: `./frontend`                               |
| 3.   | Set env var: `REACT_APP_API_BASE=<render-url>`             |
| 4.   | Deploy → Get URL: `https://order-to-cash-xxxxx.vercel.app` |

**Guides:** [RENDER_DEPLOYMENT.md](RENDER_DEPLOYMENT.md) | [VERCEL_DEPLOYMENT.md](VERCEL_DEPLOYMENT.md) | [FRONTEND_ENV_SETUP.md](FRONTEND_ENV_SETUP.md)

---

## Query Examples

| Query                                  | Returns         |
| -------------------------------------- | --------------- |
| "Show all customers"                   | 8 customers     |
| "Top 5 sales orders by amount"         | Ranked orders   |
| "Trace billing document 90504298"      | Full O2C flow   |
| "Products with most billing docs"      | Ranked products |
| "Customers with incomplete deliveries" | Filtered list   |

---

## Pre-Deploy Checklist

- [ ] Code pushed to GitHub
- [ ] `backend/.env` created (not in git)
- [ ] `backend/data/final_full_dataset.pdf` exists
- [ ] `requirements.txt` current
- [ ] `.gitignore` protects secrets
- [ ] `/api/stats` endpoint responds
- [ ] Frontend loads at `http://localhost:8000`

---

## Support

| Issue               | Solution                                 |
| ------------------- | ---------------------------------------- |
| "Could not connect" | Check `REACT_APP_API_BASE` env var       |
| Cold start (slow)   | Normal on free tier, upgrade to paid     |
| PDF not loading     | Ensure file committed in `backend/data/` |
| CORS errors         | Backend configured for Vercel domains    |

---

**Status:** ✅ Ready for Production | **Stack:** FastAPI + D3.js + SQLite + Groq

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
  #   G r a p h - B a s e d - D a t a - M o d e l i n g - a n d - Q u e r y - S y s t e m 
   
   
