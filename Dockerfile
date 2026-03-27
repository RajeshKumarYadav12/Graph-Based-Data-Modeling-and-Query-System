FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
  gcc \
  && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend folder (with code, .env, and data)
COPY backend ./backend

# Set working directory to backend for relative path resolution
WORKDIR /app/backend

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8000/api/health')"

# Run the application from backend directory
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
