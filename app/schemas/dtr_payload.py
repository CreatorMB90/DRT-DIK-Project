"""Pydantic validation schemas for the DTR payload (JSONB in dtr_rules)."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Nested sub-models
# ---------------------------------------------------------------------------


class ReorderElement(BaseModel):
    """A single reorder instruction: move ``element`` after ``move_after``."""

    element: str = Field(
        ...,
        description="CSS selector of the confidence block to move.",
        min_length=1,
    )
    move_after: str = Field(
        ...,
        description="CSS selector of the target block (under the price) where the element should be placed.",
        min_length=1,
    )

    model_config = {"extra": "forbid"}


class StructurePayload(BaseModel):
    """Structural overrides for the product page."""

    hide_elements: list[str] = Field(
        default_factory=list,
        description="CSS selectors of distracting elements to hide.",
    )
    reorder_elements: list[ReorderElement] = Field(
        default_factory=list,
        description="List of elements to relocate under the price block.",
    )

    model_config = {"extra": "forbid"}


# ---------------------------------------------------------------------------
# Root payload model — strict validation of the JSONB column
# ---------------------------------------------------------------------------


class DtrPayload(BaseModel):
    """Complete DTR payload validated before storage in ``dtr_rules.payload_texts``.

    All top-level keys are optional so a rule can target *only* texts, *only*
    images, or any combination.  Unknown keys are rejected (``extra = "forbid"``).
    """

    texts: dict[str, str] | None = Field(
        None,
        description="CSS-selector → new persuasive text mapping.",
    )
    images: dict[str, str] | None = Field(
        None,
        description="CSS-selector → new reassurance image URL mapping.",
    )
    structure: StructurePayload | None = Field(
        None,
        description="Structural modifications (hide / reorder blocks).",
    )
    styles: dict[str, dict[str, str]] | None = Field(
        None,
        description="CSS-selector → forced inline CSS properties mapping.",
    )

    model_config = {"extra": "forbid"}