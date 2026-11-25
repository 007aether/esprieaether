# ESPRIEAETHER-SUNNA Dockerfile
# Multi-stage build for the Executive Director Agent OS
# Base image: Python 3.11 with Debian Bookworm

FROM python:3.11-slim-bookworm AS base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=300

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    libffi-dev \
    libssl-dev \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r esprieaether && useradd -r -g esprieaether esprieaether

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /data /app/Sunna-Equipe-Industrial /app/evolution_reports \
    && chown -R esprieaether:esprieaether /app /data

# Switch to non-root user
USER esprieaether

# Expose ports
EXPOSE 5100 5105

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:5100/health || exit 1

# Default command: run both API and dashboard
CMD ["python", "src/sunna_executor.py"]