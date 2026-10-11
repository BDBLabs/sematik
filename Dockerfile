# syntax=docker/dockerfile:1

# ---- Stage 1: Build the React frontend ----
FROM node:20-alpine AS ui-builder
WORKDIR /app/ui
COPY ui/package.json ui/package-lock.json* ./
RUN npm ci --no-audit --no-fund 2>/dev/null || npm install --no-audit --no-fund
COPY ui/src/ ./src/
COPY ui/index.html ui/vite.config.ts ui/tsconfig.json ./
RUN npm run build

# ---- Stage 2: Python backend with uvicorn ----
FROM python:3.12-slim AS runtime
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install Python deps + the sematik package (with api extras) in one cached layer
COPY pyproject.toml ./
COPY src/ ./src/
COPY tests/fixtures/ ./tests/fixtures/
COPY api/ ./api/
RUN pip install --no-cache-dir -e ".[api]"

# Copy built UI from the frontend stage
COPY --from=ui-builder /app/ui/dist/ /app/ui/dist/

# Verify the app starts (health check)
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health')" || exit 1

EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
