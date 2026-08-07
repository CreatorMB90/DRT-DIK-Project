from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config.config import settings
from app.backend_routes.webhooks import router as webhooks_router
from app.services.supabase_client import get_supabase_client, _supabase_client

app = FastAPI(
    title="DRT Extension Shopify",
    description="Micro-SaaS de Remplacement Dynamique de Texte pour Shopify",
    version="0.1.0",
)

# ---------------------------------------------------------------------------
# Static files (frontend test page, DTR injector)
# ---------------------------------------------------------------------------

app.mount("/static", StaticFiles(directory="app/static"), name="static")

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(webhooks_router, prefix="/api/v1")

# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}