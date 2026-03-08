# syntax=docker/dockerfile:1
# Optimised for ARM64 (Raspberry Pi 5) and AMD64 (x86 servers)
FROM python:3.11-slim-bookworm

# Install system dependencies required by Playwright/Chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxext6 \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright and Chromium browser binaries
RUN playwright install chromium && playwright install-deps chromium

# Copy application source
COPY src/ ./src/

# Create data directory (will be overridden by volume mount)
RUN mkdir -p /app/data/assignments

ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1

CMD ["python", "src/main.py"]
