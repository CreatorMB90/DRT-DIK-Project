"""AI Processor — Asynchronous LLM-powered psychological rule generation.

This module contains the core async function that:
  1. Builds a persona-driven system prompt via ``prompt_templates``.
  2. Calls an OpenAI-compatible LLM API (OpenAI, DeepSeek, Groq, …).
  3. Cleans and parses the raw JSON response.
  4. Validates the payload against the strict ``DtrPayload`` Pydantic model.
  5. Persists the validated rule into Supabase.

It is designed to run as a **FastAPI Background Task** — the HTTP route
returns immediately (202), while the heavy LLM call proceeds in the
background without blocking the request cycle.
"""

from __future__ import annotations

import json
import logging
import os
import re

import httpx

from app.config.config import settings
from app.schemas.dtr_payload import DtrPayload
from app.services.prompt_templates import build_system_prompt
from app.services.supabase_client import upsert_dtr_rule

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# OpenTelemetry / tracing-friendly user-agent.
_HTTP_USER_AGENT = "DRT-Extension-Shopify/1.0 (AI-Processor)"

# Timeout for the LLM API call (seconds).  LLM responses can be slow,
# but we cap at a reasonable value so the background worker doesn't hang.
_LLM_REQUEST_TIMEOUT = 60.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_json_from_llm_response(raw_text: str) -> str:
    """Heuristically extract the JSON substring from an LLM text response.

    Handles common LLM formatting mistakes:
    * Markdown fences: ```json ... ```
    * Leading/trailing prose.
    * Multiple JSON objects (takes the first).
    """
    if not raw_text:
        raise ValueError("LLM returned an empty response")

    text = raw_text.strip()

    # 1. Try to extract code-fenced JSON block.
    fence_re = re.compile(r"```(?:json)?\s*\n?(.*?)\n?```", re.DOTALL)
    match = fence_re.search(text)
    if match:
        text = match.group(1).strip()

    # 2. Find the outermost JSON object (first '{' to matching '}').
    start = text.find("{")
    if start == -1:
        raise ValueError(
            f"No JSON object found in LLM response. First 200 chars: "
            f"{raw_text[:200]!r}"
        )

    # Walk characters to find the matching closing brace.
    depth = 0
    for i, ch in enumerate(text[start:], start=start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]

    raise ValueError(
        f"Unterminated JSON object in LLM response. "
        f"First 200 chars: {raw_text[:200]!r}"
    )


# ---------------------------------------------------------------------------
# Core async function
# ---------------------------------------------------------------------------


async def generate_and_save_psychological_rules(
    *,
    shop_domain: str,
    product_id: str,
    utm_source: str,
    product_title: str,
    product_description: str,
    theme_selectors: dict[str, str],
    plan_tier: str = "growth",
) -> None:
    """Full pipeline: prompt → LLM → validate → persist (background-safe).

    This function is decorated with a broad try/except so that **any**
    failure (network, timeout, bad JSON, validation error) is logged
    but never propagated to the background task runner (which would
    crash the worker silently).

    Parameters
    ----------
    shop_domain : str
        The myshopify.com domain (used to resolve ``shop_id``).
    product_id : str
        Shopify product ID.
    utm_source : str
        The campaign UTM source value (drives the psychological angle).
    product_title : str
        Raw product title.
    product_description : str
        Raw product description (HTML or plain text).
    theme_selectors : dict[str, str]
        Semantic-block → CSS selector mapping for the current theme.
    plan_tier : str
        "launch" (text + images + button color only) or "growth" (full
        psychological restructuring with hide/reorder).
    """
    try:
        # ── 1. Build the persona-driven system prompt ──────────────────
        system_prompt = build_system_prompt(
            utm_source=utm_source,
            product_title=product_title,
            product_description=product_description,
            theme_selectors=theme_selectors,
            plan_tier=plan_tier,
        )

        # ── 2. Call the LLM API ────────────────────────────────────────
        llm_base_url = settings.LLM_BASE_URL.rstrip("/")
        timeout = httpx.Timeout(
            connect=10.0,
            read=_LLM_REQUEST_TIMEOUT,
            write=10.0,
            pool=5.0,
        )

        async with httpx.AsyncClient(
            base_url=llm_base_url,
            timeout=timeout,
            headers={
                "Authorization": f"Bearer {settings.LLM_API_KEY}",
                "Content-Type": "application/json",
                "User-Agent": _HTTP_USER_AGENT,
            },
        ) as client:
            logger.info(
                "Calling LLM for shop=%s product=%s utm=%s plan=%s (model=%s)",
                shop_domain,
                product_id,
                utm_source,
                plan_tier,
                settings.LLM_MODEL,
            )
            response = await client.post(
                "/chat/completions",
                json={
                    "model": settings.LLM_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                    ],
                    "temperature": 0.4,  # Enough creativity, but not wild
                    "max_tokens": 2048,
                },
            )
            response.raise_for_status()

        body = response.json()

        # Extract the assistant's message text.
        choices = body.get("choices", [])
        if not choices:
            raise ValueError(
                f"LLM response contained no choices. Body: {body!r}"
            )
        raw_content: str = choices[0].get("message", {}).get("content", "")
        logger.debug("LLM raw response: %s", raw_content[:500])

        # ── 3. Clean & extract JSON ────────────────────────────────────
        json_str = _extract_json_from_llm_response(raw_content)

        # ── 4. Parse & validate against DtrPayload ─────────────────────
        raw_dict = json.loads(json_str)

        # 🔒 Post-validation: STRIP forbidden fields for Launch plan.
        # Even if the LLM disobeyed the prompt, we enforce it server-side.
        if plan_tier == "launch":
            raw_dict.pop("structure", None)
            # For Launch, only allow button color in styles:
            if "styles" in raw_dict and isinstance(raw_dict["styles"], dict):
                allowed_styles: dict[str, dict[str, str]] = {}
                for selector, props in raw_dict["styles"].items():
                    if selector in (".btn--add-to-cart", ".atc-button", "#add-to-cart"):
                        # Only keep background + color + border-radius
                        safe_props = {}
                        for prop_name in ("background", "background-color", "color", "border-radius"):
                            if prop_name in props:
                                safe_props[prop_name] = props[prop_name]
                        if safe_props:
                            allowed_styles[selector] = safe_props
                raw_dict["styles"] = allowed_styles if allowed_styles else None
            else:
                raw_dict.pop("styles", None)
            logger.info(
                "Plan Launch: stripped structure and restricted styles for product=%s",
                product_id,
            )

        validated_payload = DtrPayload.model_validate(raw_dict)

        logger.info(
            "LLM payload validated successfully for shop=%s product=%s plan=%s",
            shop_domain,
            product_id,
            plan_tier,
        )

        # ── 5. Persist to Supabase ─────────────────────────────────────
        await upsert_dtr_rule(
            shop_domain=shop_domain,
            product_id=product_id,
            utm_source=utm_source,
            payload_texts=validated_payload,
        )

        logger.info(
            "DTR rule saved for shop=%s product=%s utm=%s plan=%s",
            shop_domain,
            product_id,
            utm_source,
            plan_tier,
        )

    except Exception:
        # Broad catch: the background task MUST NOT crash the worker.
        # Log the full traceback for observability.
        logger.exception(
            "AI rule generation FAILED for shop=%s product=%s utm=%s plan=%s",
            shop_domain,
            product_id,
            utm_source,
            plan_tier,
        )
