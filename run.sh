#!/bin/bash
# run.sh – Start the Order-to-Cash Graph Query System

set -e

echo "================================================"
echo "  Order to Cash - Graph Query System"
echo "================================================"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
  echo "ERROR: python3 not found. Please install Python 3.10+"
  exit 1
fi

# Check .env
if [ ! -f ".env" ]; then
  echo "WARNING: .env not found. Creating from template..."
  cp .env.example .env 2>/dev/null || echo "GROQ_API_KEY=your_key_here" > .env
fi

# Create data directory
mkdir -p data

# Check if dataset PDF exists
PDF_PATH=$(grep PDF_PATH .env | cut -d= -f2 | tr -d '"' | xargs)
PDF_PATH=${PDF_PATH:-./data/final_full_dataset.pdf}

if [ ! -f "$PDF_PATH" ]; then
  echo ""
  echo "⚠️  Dataset PDF not found at: $PDF_PATH"
  echo "   Please copy your final_full_dataset.pdf to the data/ directory:"
  echo "   cp /path/to/final_full_dataset.pdf ./data/"
  echo ""
  echo "   The system will start with an empty database."
  echo ""
fi

# Install dependencies
echo "Installing dependencies..."
pip install -q -r requirements.txt

echo ""
echo "Starting server..."
echo "  → Frontend: http://localhost:8000"
echo "  → API Docs: http://localhost:8000/docs"
echo ""

cd backend
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
