FROM python:3.11-slim

# Prevent python from buffering stdout and writing .pyc files
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080

WORKDIR /app

# Install minimal system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code, static assets, pre-indexed RAG database, and configs
COPY backend/ ./backend/
COPY static/ ./static/
COPY data/aviation_rag.db ./data/aviation_rag.db
COPY data/leads.json ./data/leads.json
COPY data/ocr_cache/ ./data/ocr_cache/
COPY run.py .

EXPOSE 8080

# Execute uvicorn respecting Cloud Run dynamic $PORT
CMD exec uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8080}
