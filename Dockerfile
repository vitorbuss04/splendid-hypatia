# Production Dockerfile for 3D Printing Calculator & Quoting Engine
# Compatible with EasyPanel, Docker Swarm, and Standalone Docker
FROM python:3.13-slim

WORKDIR /app

# Environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=production \
    DATABASE_URL=postgresql+psycopg://postgres.your-tenant-id:124c92be406d143842e01a4c0c09fb1c@136.248.126.192:5432/postgres \
    DB_SCHEMA=3dprintcalc \
    PORT=80

# Install curl for container healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install dependencies first to leverage Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Ensure permissions
RUN chmod -R 755 /app

EXPOSE 80 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || curl -f http://localhost:80/api/health || exit 1

CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-80}"]
