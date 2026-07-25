"""Supabase client initialization and accessor."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from supabase import create_client, Client

from app.config.config import settings
from app.schemas.dtr_payload import DtrPayload

# Global client instance — initialized once at module load time.
_supabase_client: Client | None = None


def _init_supabase() -> Client:
    """Lazy-initialize and return the Supabase client singleton.

    Uses the URL and key read from ``settings`` (sourced via Pydantic
    from the ``.env`` file).
    """
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = create_client(
            supabase_url=settings.SUPABASE_URL,
            supabase_key=settings.SUPABASE_KEY,
        )
    return _supabase_client


async def get_supabase_client() -> Client:
    """Return the global Supabase client instance.

    This async wrapper makes the client injectable into FastAPI
    dependency injection without exposing the module-level variable
    directly.
    """
    return _init_supabase()


# ---------------------------------------------------------------------------
# Shop (marchand)
# ---------------------------------------------------------------------------


async def create_or_update_shop(
    shop_domain: str,
    access_token: str,
) -> dict[str, Any]:
    """Create or update a shop record (upsert on ``shops`` table).

    If a shop with the given ``shop_domain`` already exists its
    ``access_token`` is updated and ``is_active`` is forced to ``True``.
    Otherwise a new row is inserted.

    Parameters
    ----------
    shop_domain : str
        The myshopify.com domain of the merchant (unique key).
    access_token : str
        The Shopify API access token obtained during OAuth.

    Returns
    -------
    dict[str, Any]
        The first row of the upsert response (the shop record).

    Raises
    ------
    RuntimeError
        If the database operation fails.
    """
    client = _init_supabase()
    try:
        result = await asyncio.to_thread(
            client.table("shops")
            .upsert(
                {
                    "shop_domain": shop_domain,
                    "access_token": access_token,
                    "is_active": True,
                },
                ignore_duplicates=False,
                on_conflict="shop_domain",
            )
            .execute,
        )
        # The postgrest-py wrapper returns a Pydantic-like response
        # with a .data attribute containing the list of affected rows.
        data: list[dict[str, Any]] = result.data  # type: ignore[union-attr]
        if not data:
            raise RuntimeError(
                f"Upsert on shops returned no data for {shop_domain}"
            )
        return data[0]
    except Exception as exc:
        raise RuntimeError(
            f"Failed to upsert shop '{shop_domain}': {exc}"
        ) from exc


# ---------------------------------------------------------------------------
# DTR (texte dynamique)
# ---------------------------------------------------------------------------


async def get_dtr_rule(
    shop_domain: str,
    product_id: str,
    utm_source: str,
) -> dict[str, Any] | None:
    """Retrieve the DTR rule payload for a given product and UTM source.

    The function first resolves the ``shop_id`` from the ``shops`` table
    using the ``shop_domain``, then queries the ``dtr_rules`` table
    matching that shop, the given ``product_id`` and ``utm_source``.

    Parameters
    ----------
    shop_domain : str
        The myshopify.com domain identifying the merchant.
    product_id : str
        The Shopify product ID (as stored in ``dtr_rules.product_id``).
    utm_source : str
        The UTM source value (as stored in ``dtr_rules.utm_source``).

    Returns
    -------
    dict[str, Any] | None
        The matching ``dtr_rules`` row, or ``None`` if no rule exists
        or the shop is not found.

    Raises
    ------
    RuntimeError
        If a database communication error occurs.
    """
    client = _init_supabase()

    # 1. Resolve shop_domain -> shop_id
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
        raise RuntimeError(
            f"Failed to look up shop '{shop_domain}': {exc}"
        ) from exc

    shop_data_raw: Any = shop_result.data  # type: ignore[union-attr]
    # Normalise : maybe_single() peut retourner une liste [{...}] ou un dict {...}
    # selon la version du client Supabase.
    if isinstance(shop_data_raw, list):
        shop_data_raw = shop_data_raw[0] if shop_data_raw else None
    shop_data: dict[str, Any] | None = shop_data_raw

    if shop_data is None:
        # Shop does not exist -> no rule can exist
        return None

    # Normalize shop_id to a plain string (same defence as in upsert_dtr_rule).
    raw_shop_id: Any = shop_data["id"]
    shop_id: str = str(raw_shop_id)

    # 2. Fetch matching dtr_rule
    try:
        rule_result = await asyncio.to_thread(
            client.table("dtr_rules")
            .select("payload_texts")
            .eq("shop_id", shop_id)
            .eq("product_id", product_id)
            .eq("utm_source", utm_source)
            .limit(1)
            .maybe_single()
            .execute,
        )
    except Exception as exc:
        raise RuntimeError(
            f"Failed to query dtr_rules for shop={shop_domain}, "
            f"product={product_id}, utm={utm_source}: {exc}"
        ) from exc

    rule_data_raw: Any = rule_result.data  # type: ignore[union-attr]
    if isinstance(rule_data_raw, list):
        rule_data_raw = rule_data_raw[0] if rule_data_raw else None
    rule_data: dict[str, Any] | None = rule_data_raw
    return rule_data


async def upsert_dtr_rule(
    shop_domain: str,
    product_id: str,
    utm_source: str,
    payload_texts: DtrPayload | dict[str, Any],
) -> dict[str, Any]:
    """Create or update a DTR rule (upsert on ``dtr_rules`` table).

    Resolves the ``shop_id`` from the ``shops`` table using the given
    ``shop_domain``, then upserts a row in ``dtr_rules`` keyed on
    ``(shop_id, product_id, utm_source)``.

    Parameters
    ----------
    shop_domain : str
        The myshopify.com domain identifying the merchant.
    product_id : str
        The Shopify product ID.
    utm_source : str
        The UTM source value.
    payload_texts : DtrPayload | dict[str, Any]
        The validated DTR payload (Pydantic model or raw dict).

    Returns
    -------
    dict[str, Any]
        The first row of the upsert response.

    Raises
    ------
    RuntimeError
        If the shop does not exist or the database operation fails.
    """
    client = _init_supabase()

    # 1. Resolve shop_domain -> shop_id
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
        raise RuntimeError(
            f"Failed to look up shop '{shop_domain}': {exc}"
        ) from exc

    shop_data_raw: Any = shop_result.data  # type: ignore[union-attr]
    # Normalise : maybe_single() peut retourner une liste [{...}] ou un dict {...}
    # selon la version du client Supabase.
    if isinstance(shop_data_raw, list):
        shop_data_raw = shop_data_raw[0] if shop_data_raw else None
    shop_data: dict[str, Any] | None = shop_data_raw

    if shop_data is None:
        raise RuntimeError(
            f"Shop '{shop_domain}' not found — cannot upsert DTR rule"
        )

    # Normalize shop_id to a plain string so PostgreSQL / Supabase
    # does not choke on an UUID Python object.
    raw_shop_id: Any = shop_data["id"]
    shop_id: str = str(raw_shop_id)

    # Normalize payload_texts: if it is a Pydantic model, convert to dict;
    # if it arrived as a JSON string (e.g. because the client sent
    # Content-Type text/plain), convert it back to a dict.
    _payload: Any = payload_texts
    if isinstance(_payload, DtrPayload):
        _payload = _payload.model_dump(exclude_none=True)
    elif isinstance(_payload, str):
        _payload = json.loads(_payload)

    # 2. Upsert dtr_rule
    try:
        result = await asyncio.to_thread(
            client.table("dtr_rules")
            .upsert(
                {
                    "shop_id": shop_id,
                    "product_id": product_id,
                    "utm_source": utm_source,
                    "payload_texts": _payload,
                },
                ignore_duplicates=False,
                on_conflict="shop_id,product_id,utm_source",
            )
            .execute,
        )
    except Exception as exc:
        raise RuntimeError(
            f"Failed to upsert dtr_rule for shop={shop_domain}, "
            f"product={product_id}, utm={utm_source}: {exc}"
        ) from exc

    data: list[dict[str, Any]] = result.data  # type: ignore[union-attr]
    if not data:
        raise RuntimeError(
            f"Upsert on dtr_rules returned no data for "
            f"shop={shop_domain}, product={product_id}, utm={utm_source}"
        )
    return data[0]