FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_ENV=production

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY deployment_clean/requirements.txt requirements.txt
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY app.py .
COPY main.py .
COPY models.py .
COPY rag_chain.py .
COPY vectorizer.py .
COPY session_memory.py .
COPY ai_tool_executor.py .
COPY api_executor.py .
COPY static/ ./static/
COPY templates/ ./templates/

# Create directories
RUN mkdir -p uploads faiss_index logs static/widget_icons static/logos

# Set permissions
RUN chmod -R 755 /app

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "120", "main:app"]