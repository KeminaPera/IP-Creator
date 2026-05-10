# Multi-stage build for IP Creator

# ============================================
# Stage 1: Build Frontend
# ============================================
FROM node:18-alpine AS frontend-builder

WORKDIR /frontend

# Copy frontend files
COPY frontend-vue/package*.json ./
RUN npm install

COPY frontend-vue/ .
RUN npm run build

# ============================================
# Stage 2: Backend Application
# ============================================
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application code
COPY app/ ./app/
COPY celery_worker.py .
COPY init_database.py .

# Copy built frontend from Stage 1
COPY --from=frontend-builder /frontend/dist ./frontend-vue/dist

# Create necessary directories
RUN mkdir -p data/ip_assets data/lora_models data/videos data/stories data/models data/exports logs

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose ports
EXPOSE 80 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Default command - start backend
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
