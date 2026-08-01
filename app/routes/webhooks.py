"""Webhook routes for Shopify merchant integration."""

import json
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel

from app.schemas.dtr_payload import DtrPayload
from app.services.ai_processor import generate_and_save_psychological_rules
from app.services.supabase_client import (
    create_or_update_shop,
    get_dtr_rule,
    get_supabase_client,
    upsert_dtr_rule,
)

router = APIRouter(prefix="/shopify", tags=["shopify"])

# ---------------------------------------------------------------------------
# Plan tiers — performance-gated billing
# ---------------------------------------------------------------------------

VALID_PLAN_TIERS = ("launch", "growth")


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class InstallPayload(BaseModel):
    """Payload expected by the POST /shopify/install endpoint."""

    shop_domain: str
    access_token: str


class InstallResponse(BaseModel):
    """Response returned after a successful upsert."""

    status: str
    message: str


class RulePayload(BaseModel):
    """Payload for creating or updating a DTR rule."""

    shop_domain: str
    product_id: str
    utm_source: str
    payload_texts: DtrPayload


class GenerateRulePayload(BaseModel):
    """Payload for AI-powered psychological rule generation.

    The route returns immediately (202 Accepted) and the actual LLM
    call + DB upsert happens in a background task.
    """

    shop_domain: str
    product_id: str
    utm_source: str
    product_title: str
    product_description: str = ""
    theme_selectors: dict[str, str] = {}


# ---------------------------------------------------------------------------
# Routes — Installation
# ---------------------------------------------------------------------------


@router.post("/install", response_model=InstallResponse)
async def install_shop(payload: InstallPayload) -> InstallResponse:
    """Register or update a Shopify merchant in the database.

    Expects a JSON body with ``shop_domain`` and ``access_token``.
    Delegates the upsert to ``create_or_update_shop`` and returns a
    confirmation JSON object.

    Raises
    ------
    HTTPException 500
        If the database operation fails.
    """
    try:
        await create_or_update_shop(
            shop_domain=payload.shop_domain,
            access_token=payload.access_token,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {exc}",
        ) from exc

    return InstallResponse(
        status="success",
        message="Shop configured successfully",
    )


# ---------------------------------------------------------------------------
# Routes — DTR rules
# ---------------------------------------------------------------------------


@router.post("/rules")
async def create_rule(payload: RulePayload) -> dict[str, str]:
    """Create or update a DTR rule for a given product and UTM source.

    The endpoint resolves the ``shop_id`` from the ``shop_domain``,
    then upserts the rule in the ``dtr_rules`` table.

    Returns
    -------
    dict[str, str]
        A success message.

    Raises
    ------
    HTTPException 500
        If the database operation fails (including missing shop).
    """
    try:
        await upsert_dtr_rule(
            shop_domain=payload.shop_domain,
            product_id=payload.product_id,
            utm_source=payload.utm_source,
            payload_texts=payload.payload_texts,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {exc}",
        ) from exc

    return {"status": "success", "message": "Rule saved successfully"}


@router.get("/rules")
async def get_rule(
    shop_domain: str = Query(..., description="The myshopify.com domain"),
    product_id: str = Query(..., description="The Shopify product ID"),
    utm_source: str = Query(..., description="The UTM source value"),
) -> dict[str, Any]:
    """Retrieve the DTR payload for a specific product and UTM source.

    Parameters are passed as query string parameters.

    Returns
    -------
    dict[str, Any]
        The ``payload_texts`` JSON object, wrapped in a response dict.

    Raises
    ------
    HTTPException 404
        If no rule exists for the given combination.
    HTTPException 500
        If a database communication error occurs.
    """
    try:
        rule = await get_dtr_rule(
            shop_domain=shop_domain,
            product_id=product_id,
            utm_source=utm_source,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {exc}",
        ) from exc

    if rule is None or rule.get("payload_texts") is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No rule found for shop={shop_domain}, "
                f"product={product_id}, utm={utm_source}"
            ),
        )

    # Normalize payload_texts: Supabase may return it as a JSON string
    # depending on the client library version. Ensure it's a dict.
    payload: Any = rule["payload_texts"]
    if isinstance(payload, str):
        payload = json.loads(payload)

    return payload


# ---------------------------------------------------------------------------
# Route — Rule count per product (for dashboard)
# ---------------------------------------------------------------------------


@router.get("/rules/count")
async def count_rules(
    shop_domain: str = Query(..., description="The myshopify.com domain"),
    product_id: str = Query(..., description="The Shopify product ID"),
) -> dict[str, int]:
    """Return the number of DTR rules for a given shop + product.

    Used by the Remix dashboard IndexTable to show "Optimisé" badges.
    """
    import asyncio

    client = await get_supabase_client()

    # Resolve shop_id
    try:
        shop_result = await asyncio.to_thread(
            client.table("shops")
            .select("id")
            .eq("shop_domain", shop_domain)
            .limit(1)
            .maybe_single()
            .execute,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {exc}",
        ) from exc

    shop_data_raw: Any = shop_result.data  # type: ignore[union-attr]
    if isinstance(shop_data_raw, list):
        shop_data_raw = shop_data_raw[0] if shop_data_raw else None
    if shop_data_raw is None:
        return {"count": 0}

    shop_id: str = str(shop_data_raw["id"])

    # Count matching rules
    try:
        count_result = await asyncio.to_thread(
            client.table("dtr_rules")
            .select("id", count="exact")
            .eq("shop_id", shop_id)
            .eq("product_id", product_id)
            .execute,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {exc}",
        ) from exc

    total = count_result.count if hasattr(count_result, "count") else len(count_result.data or [])  # type: ignore[arg-type]
    return {"count": total}


# ---------------------------------------------------------------------------
# Route — AI-powered optimization from Remix dashboard
# ---------------------------------------------------------------------------


class OptimizePayload(BaseModel):
    """Payload sent from the Remix dashboard to trigger AI optimization."""

    shop_domain: str
    product_id: str
    product_title: str
    product_description: str = ""
    utm_source: str
    plan_tier: str = "launch"
    theme_selectors: str = "{}"  # JSON string of {name: selector}


@router.post("/optimize", status_code=202)
async def optimize_product(
    payload: OptimizePayload,
    background_tasks: BackgroundTasks,
) -> dict[str, str]:
    """Launch AI optimization for a single product (plan-gated).

    The endpoint validates the plan tier, parses theme selectors, then
    delegates the LLM call to a ``BackgroundTasks`` worker. The HTTP
    response is returned immediately with status ``202 Accepted``.

    Plan gating:
      - ``launch``: Only text + images + button color.
      - ``growth``: Full psychological restructuring.
    """
    # Validate plan tier
    plan_tier = payload.plan_tier.lower()
    if plan_tier not in VALID_PLAN_TIERS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid plan_tier '{plan_tier}'. "
                f"Must be one of: {', '.join(VALID_PLAN_TIERS)}"
            ),
        )

    # Parse theme selectors
    try:
        theme_selectors: dict[str, str] = json.loads(payload.theme_selectors)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid theme_selectors JSON: {exc}",
        ) from exc

    # Dispatch to background task
    background_tasks.add_task(
        generate_and_save_psychological_rules,
        shop_domain=payload.shop_domain,
        product_id=payload.product_id,
        utm_source=payload.utm_source,
        product_title=payload.product_title,
        product_description=payload.product_description,
        theme_selectors=theme_selectors,
        plan_tier=plan_tier,
    )

    return {
        "status": "accepted",
        "message": (
            f"AI optimization launched for product={payload.product_id} "
            f"(plan={plan_tier}, utm={payload.utm_source}). "
            f"The rule will be saved asynchronously."
        ),
    }


# ---------------------------------------------------------------------------
# Routes — AI-powered rule generation (background task)
# ---------------------------------------------------------------------------


@router.post("/generate-rule", status_code=202)
async def generate_rule(
    payload: GenerateRulePayload,
    background_tasks: BackgroundTasks,
) -> dict[str, str]:
    """Launch AI-powered psychological rule generation in the background.

    The endpoint validates the input, then defers the heavy LLM call to a
    ``BackgroundTasks`` worker.  The HTTP response is returned immediately
    with status ``202 Accepted`` — the caller does **not** wait for the AI
    to finish.

    The background task will:
      1. Build the persona-driven prompt.
      2. Call the LLM API (OpenAI / DeepSeek compatible).
      3. Parse & validate the response against ``DtrPayload``.
      4. Upsert the validated payload into ``dtr_rules``.

    Failures in the background task are logged but **never** propagated
    to the client (the route always returns 202 if the input is valid).
    """
    # ── Plan-gating: detect the plan tier from the payload or default ─
    # The GenerateRulePayload does not carry plan_tier explicitly (it is
    # a legacy/internal endpoint). Default to "launch" for safety so
    # structure/styling are stripped server-side unless explicitly
    # overridden.
    plan_tier = getattr(payload, "plan_tier", None) or "launch"
    if plan_tier not in VALID_PLAN_TIERS:
        plan_tier = "launch"

    background_tasks.add_task(
        generate_and_save_psychological_rules,
        shop_domain=payload.shop_domain,
        product_id=payload.product_id,
        utm_source=payload.utm_source,
        product_title=payload.product_title,
        product_description=payload.product_description,
        theme_selectors=payload.theme_selectors,
        plan_tier=plan_tier,
    )

    return {
        "status": "accepted",
        "message": (
            f"AI generation launched for product={payload.product_id} "
            f"(utm={payload.utm_source}). The rule will be saved "
            f"asynchronously."
        ),
    }
