# 📊 Order-to-Cash Graph System

**Graph-based data modeling & LLM-powered query interface for O2C business processes**

---

## 🎯 Overview

| Aspect         | Details                    |
| -------------- | -------------------------- |
| **Framework**  | FastAPI + D3.js + NetworkX |
| **Database**   | SQLite                     |
| **LLM**        | Groq API (LLaMA 3.3)       |
| **Deployment** | Render + Vercel            |

---


## ⚙️ Local Development

### Setup

```bash
pip install -r requirements.txt
cd backend
uvicorn main:app --reload

Open: http://localhost:8000

Environment Variables
GROQ_API_KEY=your_key
PDF_PATH=./data/final_full_dataset.pdf
DB_PATH=./data/otc.db
REACT_APP_API_BASE=http://localhost:8000

---

🔌 API Endpoints
Endpoint	Method	Description
/	GET	Frontend HTML
/api/graph	GET	Graph JSON
/api/stats	GET	Dataset stats
/api/query	POST	NL query
/api/node/{id}	GET	Node details

---

🧠 Data Model

Nodes:
Customer → SalesOrder → SalesOrderItem → (Delivery, Billing) → JournalEntry

Key Entities:
Customer, SalesOrder, SalesOrderItem, Delivery, DeliveryItem, BillingDoc, BillingItem, JournalEntry, Product

---

🤖 LLM Pipeline

Flow:

User Query → NL→SQL (Groq) → Execute → SQL→Answer → Highlight Nodes
Features
Domain guardrails (O2C keywords only)
Conversation memory (8 messages)
Dynamic model selection
Natural language explanations

---

🛡️ Guardrails

Blocked:
Jokes, weather, politics, math, translation

Allowed:
Keywords required → order, delivery, billing, customer, material, product, journal



🚀 Deployment
Backend (Render)
Connect GitHub repo
Root Directory: (empty)
Dockerfile Path: ./Dockerfile
Set GROQ_API_KEY
Deploy
Frontend (Vercel)
Import GitHub repo
Root Directory: frontend
Set REACT_APP_API_BASE to Render URL
Deploy


📝 Example Queries
Show all customers
Top sales orders by amount
Trace billing document 90504298
Products with most billing docs
Customers with incomplete deliveries


📁 Project Structure
backend/           # FastAPI / SQLite
frontend/          # D3.js visualization
data/              # PDF + database
Dockerfile         # Docker config
requirements.txt   # Dependencies


🐳 Docker
docker compose up
docker build -t order-to-cash .
docker run -p 8000:8000 order-to-cash
✨ Features
NL → SQL automatic translation
Force-directed D3.js visualization
Node highlighting for results
Conversation memory (8 messages)
SQL transparency
Zoom, pan, drag controls



📊 Architecture Decisions

SQLite
Zero-config, fast queries, suitable for NL→SQL over ~4K records

NetworkX
In-memory graph, fast traversal, D3.js JSON export

Groq API
Fast LLM, efficient SQL generation, cost-effective

Frontend Served by Backend
Simplifies deployment and avoids CORS issues

Vercel + Render
Decoupled architecture, easy scaling



🎓 LLM Prompting Strategy
Two-Call Pipeline
Generate SQL using schema + prompt
Convert results into natural language answer
Guardrails
Regex-based filtering
Keyword validation (O2C domain only)


📜 License

Educational & business use only



📊 Query Examples
Query	Returns
Show all customers	Customer list
Top 5 sales orders by amount	Ranked orders
Trace billing document 90504298	Full O2C flow
Products with most billing docs	Ranked products
Customers with incomplete deliveries	Filtered list


✅ Pre-Deploy Checklist
Code pushed to GitHub
backend/.env created (not committed)
Dataset PDF available
requirements.txt updated
.gitignore configured
API endpoints working
Frontend loads locally


🛠️ Support
Issue	Solution
Connection error	Check REACT_APP_API_BASE
Slow startup	Expected on free tier
PDF not loading	Verify dataset path
CORS issues	Configure backend properly


📁 Full Project Structure
order-to-cash/
├── backend/
│   ├── main.py
│   ├── database.py
│   ├── data_processor.py
│   ├── graph_builder.py
│   └── llm_service.py
├── frontend/
│   └── index.html
├── data/
├── requirements.txt
├── .env
├── run.sh
└── README.md


🚀 Status

Ready for Production
Stack: FastAPI + D3.js + SQLite + Groq


⭐ Bonus Features
Natural language → SQL conversion
Node highlighting
Conversation memory (last 8 messages)
Dynamic model selection
Streaming-ready responses
Interactive graph exploration
SQL transparency in UI
