# syntax=docker/dockerfile:1

# --- Builder stage ---
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies in a virtualenv
COPY requirements.txt .
RUN python -m venv /venv \
    && /venv/bin/pip install --upgrade pip \
    && /venv/bin/pip install --no-cache-dir -r requirements.txt

# --- Final stage ---
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies (for unstructured, pdf, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 \
    poppler-utils \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Copy virtualenv from builder
COPY --from=builder /venv /venv

# Copy application code
COPY app ./app
COPY run_api.py ./
COPY app/config.py ./app/config.py

# Set environment variables
ENV PATH="/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV OPENAI_API_KEY=""
ENV GOOGLE_API_KEY=""
ENV EMBEDDING_PROVIDER="huggingface"
ENV LLM_PROVIDER="openai"

# Expose port
EXPOSE 8000

# Start the FastAPI app with uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]