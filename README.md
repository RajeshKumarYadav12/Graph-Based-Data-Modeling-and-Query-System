Order to Cash — Tab-Based Documentation Structure

🧭 Tab 1: Overview
Project Type: Context Graph + LLM Query System
Domain: Order-to-Cash (O2C)
Core Idea:
Convert business data → Graph → Query using Natural Language
Key Features:
Graph visualization (D3.js)
Natural Language → SQL → Answer
LLM-powered analytics (Groq API)
SQLite-based backend
🏗️ Tab 2: Architecture
Frontend
HTML + D3.js
Graph visualization (Force-directed)
Chat interface
Backend (FastAPI)
data_processor → PDF → SQLite
graph_builder → NetworkX → Graph JSON
llm_service → NL → SQL → Answer
Database
SQLite (single-file DB)
Tables:
customers
sales_orders
delivery
billing
journal_entries
products
🔗 Tab 3: Graph Model
Nodes
Customer
SalesOrder
SalesOrderItem
Delivery
DeliveryItem
BillingDoc
BillingItem
JournalEntry
Product
Relationships
Customer → SalesOrder
SalesOrder → Items
Items → Delivery
Items → Billing
Billing → JournalEntry
🗄️ Tab 4: Database Choice
Why SQLite?
No setup required
Lightweight (~3800 records)
Supports SQL joins
Ideal for LLM-generated SQL
Trade-off
Not scalable → Use PostgreSQL + Neo4j in production
🤖 Tab 5: LLM Pipeline
Step 1: SQL Generation
Input: Natural language
Output: SQL query + explanation
Step 2: Answer Generation
Input: SQL + results
Output: Business-friendly answer
Model
Groq models (LLaMA variants preferred)
🛡️ Tab 6: Guardrails
1. Pattern Filtering

Blocks:

Jokes / stories
Weather / politics
Math queries
Translation
2. Domain Check
Must include keywords:
order, delivery, billing, customer, etc.
Response for Invalid Queries

Only answers O2C-related questions

⚙️ Tab 7: Setup & Running
Requirements
Python 3.10+
Groq API key
Steps
Clone repo
Add .env
Add dataset PDF
Run script
Manual Run
pip install -r requirements.txt
cd backend
uvicorn main:app
🔌 Tab 8: API Endpoints
Endpoint	Method	Purpose
/api/graph	GET	Graph data
/api/query	POST	NL query
/api/node/{id}	GET	Node details
/api/stats	GET	Stats
/api/health	GET	Health
/api/reload	POST	Reload data
/docs	GET	API docs
🚀 Tab 9: Deployment
Architecture
Backend → Render (Docker)
Frontend → Vercel
Steps
Deploy backend (Render)
Deploy frontend (Vercel)
Connect API
Env Variables

Backend

GROQ_API_KEY
PDF_PATH
DB_PATH

Frontend

API Base URL
💻 Tab 10: Development
Local Dev
Run backend
Open browser
Docker
docker compose up
📊 Tab 11: Example Queries
Top products by billing
Trace billing flow
Orders not delivered
Top customers
Delivered but not billed
Top sales orders
Journal entries
Cancelled billing docs
📁 Tab 12: Project Structure
backend/
frontend/
data/
requirements.txt
.env
run.sh
README.md
✨ Tab 13: Features
NL → SQL (dynamic)
Graph highlighting
Conversation memory
Model auto-selection
Streaming responses
Graph clustering
Expandable nodes
Zoom & pan
SQL transparency
📜 Tab 14: License
Educational & business use
