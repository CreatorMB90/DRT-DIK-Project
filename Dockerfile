# ──────────────────────────────────────────────────────────────────────────────
# DTR Backend FastAPI — Production Docker Image
#
# Target platforms: Render, Railway, Fly.io, or any container host.
#
# Build:
#   docker build -t dtr-backend .
#
# Run:
#   docker run -p 8000:8000 --env-file .env dtr-backend
# ──────────────────────────────────────────────────────────────────────────────

FROM python:3.12-slim

# ── Metadata ─────────────────────────────────────────────────────────────────
LABEL app="dtr-backend"
LABEL description="DRT Extension Shopify — Micro-SaaS de Remplacement Dynamique de Texte"
LABEL maintainer="dev@dtr-extension.com"

# ── System dependencies ──────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ── Non-root user ────────────────────────────────────────────────────────────
RUN groupadd -r dtr && useradd -r -g dtr -m -d /home/dtr dtr

# ── Working directory ────────────────────────────────────────────────────────
WORKDIR /app

# ── Copy dependency file first (layer caching) ───────────────────────────────
COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ── Copy application code ────────────────────────────────────────────────────
COPY app/ ./app/

# ── Ensure static directory exists ───────────────────────────────────────────
RUN mkdir -p /app/app/static

# ── Ownership ────────────────────────────────────────────────────────────────
RUN chown -R dtr:dtr /app

# ── Drop to non-root user ────────────────────────────────────────────────────
USER dtr

# ── Expose port ──────────────────────────────────────────────────────────────
EXPOSE 8000

# ── Health check ─────────────────────────────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# ── Start Uvicorn with optimal production settings ───────────────────────────
CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--proxy-headers", \
     "--forwarded-allow-ips", "*", \
     "--log-level", "info"]