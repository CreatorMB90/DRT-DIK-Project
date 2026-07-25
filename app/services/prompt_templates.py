"""LLM Prompt Templates — Psychological Targeting Engine for DTR.

This module builds ultra-authoritative system prompts that instruct a
CRO-expert LLM (DeepSeek / OpenAI) to analyse a Shopify product page and
return a **strictly-formatted** ``DtrPayload`` JSON object.

The psychological angle is derived from the UTM source (e.g. ``tiktok_securite``
triggers a *Maximum Reassurance* persona, ``fb_scarcity`` triggers *Urgency*).
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Psychological Angle Mapping (UTM → CRO Persona)
# ---------------------------------------------------------------------------

# Each entry defines the *System Prompt block* that describes the persona's
# mission, its text-style guidelines and which visual elements to favour.
_UTM_ANGLE_MAP: dict[str, dict[str, str]] = {
    # ── RÉASSURANCE / SÉCURITÉ ──────────────────────────────────────────
    "secure": {
        "persona": "EXPERT EN RÉASSURANCE MAXIMALE",
        "mission": (
            "Votre mission est de RASSURER l'acheteur à chaque étape. "
            "Le produit vedette doit respirer la confiance : garanties, "
            "certifications, avis clients vérifiés, politique de retour "
            "flexible. Toute friction mentale doit être dissoute."
        ),
        "text_style": (
            "Privilégiez des formulations rassurantes et factuelles : "
            "\"100 % satisfait ou remboursé\", \"Paiement 100 % sécurisé\", "
            "\"Livraison suivie offerte\". Pas d'hyperbole agressive."
        ),
        "visual_strategy": (
            "REMONTEZ les badges de sécurité et les certifications "
            "juste après le prix. Affichez une bannière de garantie. "
            "Le bouton d'achat doit mentionner la sécurité."
        ),
    },
    "securite": {
        "persona": "EXPERT EN RÉASSURANCE MAXIMALE",
        "mission": (
            "Votre mission est de RASSURER l'acheteur à chaque étape. "
            "Le produit vedette doit respirer la confiance : garanties, "
            "certifications, avis clients vérifiés, politique de retour "
            "flexible. Toute friction mentale doit être dissoute."
        ),
        "text_style": (
            "Privilégiez des formulations rassurantes et factuelles : "
            "\"100 % satisfait ou remboursé\", \"Paiement 100 % sécurisé\", "
            "\"Livraison suivie offerte\". Pas d'hyperbole agressive."
        ),
        "visual_strategy": (
            "REMONTEZ les badges de sécurité et les certifications "
            "juste après le prix. Affichez une bannière de garantie. "
            "Le bouton d'achat doit mentionner la sécurité."
        ),
    },
    # ── URGENCE / RARETÉ ─────────────────────────────────────────────────
    "urgence": {
        "persona": "EXPERT EN URGENCE ET RARETÉ (SCARCITY)",
        "mission": (
            "Votre mission est de CRÉER UNE URGENCE IRRÉSISTIBLE. "
            "Le client doit sentir que le produit vedette est sur le point "
            "de disparaître. Utilisez la preuve sociale de masse et les "
            "compteurs de stock limité."
        ),
        "text_style": (
            "Utilisez des déclencheurs d'urgence : \"Plus que 3 en stock\", "
            "\"Vente flash — se termine dans 2 h\", \"X personnes regardent "
            "cet article en ce moment\". Texte court, percutant, chiffré."
        ),
        "visual_strategy": (
            "REMONTEZ les avis clients et le compteur de ventes "
            "juste après le prix. Ajoutez un compte à rebours ou un "
            "badge \"stock limité\" en haut de page. Supprimez les "
            "sections qui diluent l'urgence (blog, newsletter)."
        ),
    },
    "scarcity": {
        "persona": "EXPERT EN URGENCE ET RARETÉ (SCARCITY)",
        "mission": (
            "Votre mission est de CRÉER UNE URGENCE IRRÉSISTIBLE. "
            "Le client doit sentir que le produit vedette est sur le point "
            "de disparaître. Utilisez la preuve sociale de masse et les "
            "compteurs de stock limité."
        ),
        "text_style": (
            "Utilisez des déclencheurs d'urgence : \"Plus que 3 en stock\", "
            "\"Vente flash — se termine dans 2 h\", \"X personnes regardent "
            "cet article en ce moment\". Texte court, percutant, chiffré."
        ),
        "visual_strategy": (
            "REMONTEZ les avis clients et le compteur de ventes "
            "juste après le prix. Ajoutez un compte à rebours ou un "
            "badge \"stock limité\" en haut de page. Supprimez les "
            "sections qui diluent l'urgence (blog, newsletter)."
        ),
    },
    # ── PREUVE SOCIALE / AVIS ────────────────────────────────────────────
    "social": {
        "persona": "EXPERT EN PREUVE SOCIALE",
        "mission": (
            "Votre mission est de DÉMONTRER que des milliers de clients "
            "satisfaits ont déjà acheté le produit vedette. Les témoignages, "
            "notes et photos clients sont votre arme absolue."
        ),
        "text_style": (
            "Multipliez les citations de clients : \"Comme Sophie, rejoignez "
            "les 10 000 clients conquis\". Utilisez des étoiles ★★★★★ et "
            "des pourcentages de satisfaction."
        ),
        "visual_strategy": (
            "REMONTEZ le bloc d'avis juste après le prix (ou en premier). "
            "Affichez la note moyenne en haut de page. Masquez les blocs "
            "qui concurrencent la preuve sociale (produits similaires)."
        ),
    },
    "reviews": {
        "persona": "EXPERT EN PREUVE SOCIALE",
        "mission": (
            "Votre mission est de DÉMONTRER que des milliers de clients "
            "satisfaits ont déjà acheté le produit vedette. Les témoignages, "
            "notes et photos clients sont votre arme absolue."
        ),
        "text_style": (
            "Multipliez les citations de clients : \"Comme Sophie, rejoignez "
            "les 10 000 clients conquis\". Utilisez des étoiles ★★★★★ et "
            "des pourcentages de satisfaction."
        ),
        "visual_strategy": (
            "REMONTEZ le bloc d'avis juste après le prix (ou en premier). "
            "Affichez la note moyenne en haut de page. Masquez les blocs "
            "qui concurrencent la preuve sociale (produits similaires)."
        ),
    },
    # ── DESIGN / ÉPURATION ───────────────────────────────────────────────
    "design": {
        "persona": "EXPERT EN ÉPURATION VISUELLE (AESTHETIC)",
        "mission": (
            "Votre mission est de CRÉER UNE EXPÉRIENCE LUXE ET ÉPURÉE. "
            "Le produit vedette doit être présenté comme une œuvre d'art. "
            "Supprimez toute distraction visuelle pour créer un tunnel "
            "d'attention vers l'achat."
        ),
        "text_style": (
            "Utilisez un ton premium, minimaliste, suggestif. Peu de mots, "
            "beaucoup d'impact. Pas de points d'exclamation. Privilégiez "
            "les descriptions sensorielles et évocatrices."
        ),
        "visual_strategy": (
            "MASQUEZ tout élément superflu : produits connexes, sidebar, "
            "newsletter, promotions croisées. REMONTEZ une image de "
            "réassurance de haute qualité (ex: icône livraison premium) "
            "juste après le prix. Forcez des couleurs sobres et élégantes "
            "(noir, blanc, or discret) via le champ 'styles'."
        ),
    },
    "aesthetic": {
        "persona": "EXPERT EN ÉPURATION VISUELLE (AESTHETIC)",
        "mission": (
            "Votre mission est de CRÉER UNE EXPÉRIENCE LUXE ET ÉPURÉE. "
            "Le produit vedette doit être présenté comme une œuvre d'art. "
            "Supprimez toute distraction visuelle pour créer un tunnel "
            "d'attention vers l'achat."
        ),
        "text_style": (
            "Utilisez un ton premium, minimaliste, suggestif. Peu de mots, "
            "beaucoup d'impact. Pas de points d'exclamation. Privilégiez "
            "les descriptions sensorielles et évocatrices."
        ),
        "visual_strategy": (
            "MASQUEZ tout élément superflu : produits connexes, sidebar, "
            "newsletter, promotions croisées. REMONTEZ une image de "
            "réassurance de haute qualité (ex: icône livraison premium) "
            "juste après le prix. Forcez des couleurs sobres et élégantes "
            "(noir, blanc, or discret) via le champ 'styles'."
        ),
    },
    # ── VALEUR / PRIX ────────────────────────────────────────────────────
    "prix": {
        "persona": "EXPERT EN PERCEPTION DE VALEUR",
        "mission": (
            "Votre mission est de JUSTIFIER LE PRIX en démontrant une "
            "valeur exceptionnelle. Le client doit comprendre qu'il fait "
            "une affaire en or en achetant maintenant."
        ),
        "text_style": (
            "Utilisez des comparaisons et des économies chiffrées : "
            "\"Économisez 30 % aujourd'hui\", \"Valeur réelle : 199 €\". "
            "Mettez en avant le rapport qualité/prix et les bénéfices "
            "concrets du produit."
        ),
        "visual_strategy": (
            "REMONTEZ les éléments de valeur juste après le prix (badges "
            "\"Meilleur rapport qualité/prix\", \"Élu produit de l'année\"). "
            "Masquez les distractions qui pourraient faire hésiter sur le "
            "prix."
        ),
    },
    "value": {
        "persona": "EXPERT EN PERCEPTION DE VALEUR",
        "mission": (
            "Votre mission est de JUSTIFIER LE PRIX en démontrant une "
            "valeur exceptionnelle. Le client doit comprendre qu'il fait "
            "une affaire en or en achetant maintenant."
        ),
        "text_style": (
            "Utilisez des comparaisons et des économies chiffrées : "
            "\"Économisez 30 % aujourd'hui\", \"Valeur réelle : 199 €\". "
            "Mettez en avant le rapport qualité/prix et les bénéfices "
            "concrets du produit."
        ),
        "visual_strategy": (
            "REMONTEZ les éléments de valeur juste après le prix (badges "
            "\"Meilleur rapport qualité/prix\", \"Élu produit de l'année\"). "
            "Masquez les distractions qui pourraient faire hésiter sur le "
            "prix."
        ),
    },
}

# Fallback persona when no UTM keyword matches.
_DEFAULT_ANGLE: dict[str, str] = {
    "persona": "EXPERT EN CONVERSION GÉNÉRALISTE (CRO)",
    "mission": (
        "Votre mission est de MAXIMISER LE TAUX DE CONVERSION de la page "
        "produit. Analysez le produit et la structure de la page, puis "
        "appliquez les meilleures pratiques de neuromarketing : clarté, "
        "réassurance, preuve sociale et appel à l'action irrésistible."
    ),
    "text_style": (
        "Texte persuasif, bénéfices orientés client, phrases courtes, "
        "vocabulaire émotionnel mais crédible. Pas de jargon technique."
    ),
    "visual_strategy": (
        "Placez les éléments de confiance (avis, badges, garanties) juste "
        "après le prix. Masquez les éléments distrayants (produits liés, "
        "newsletter, sidebar). Le tunnel d'attention doit être sans couture."
    ),
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def resolve_angle(utm_source: str) -> dict[str, str]:
    """Return the psychological-angle descriptor dict for a given UTM value.

    The matching is case-insensitive and based on keyword containment.
    If no keyword is recognised, ``_DEFAULT_ANGLE`` is returned.
    """
    utm_key = utm_source.lower()
    for keyword, angle in _UTM_ANGLE_MAP.items():
        if keyword in utm_key:
            return angle
    return _DEFAULT_ANGLE


# ── JSON Schema embedded inside the system prompt ────────────────────────
# We inline the expected schema so the prompt is self-contained (no Python
# dependency leak). This is the *contract* the LLM must obey.
_DTR_JSON_SCHEMA = """
{
  "texts": {
    "type": "object",
    "description": "CSS selector → new persuasive text. Example: {\".product-title\": \"Le sac révolutionnaire\", \".cta-button\": \"Je commande maintenant\"}",
    "optional": true
  },
  "images": {
    "type": "object",
    "description": "CSS selector → new reassurance image URL. Example: {\".trust-badge\": \"https://cdn.example.com/secure.png\"}",
    "optional": true
  },
  "structure": {
    "type": "object",
    "description": "Structural modifications (hide & reorder elements).",
    "properties": {
      "hide_elements": {
        "type": "array",
        "items": {"type": "string"},
        "description": "CSS selectors to hide (display:none). Example: [\".related-products\", \".newsletter\"]",
        "optional": true
      },
      "reorder_elements": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "element": {"type": "string", "description": "CSS selector of the block to MOVE"},
            "move_after": {"type": "string", "description": "CSS selector of the target block AFTER which to insert the element"}
          },
          "required": ["element", "move_after"]
        },
        "description": "Move confidence blocks right after the price. Example: [{\"element\": \".trust-badges\", \"move_after\": \".product-price\"}]",
        "optional": true
      }
    },
    "optional": true
  },
  "styles": {
    "type": "object",
    "description": "CSS selector → forced inline CSS properties. Example: {\".atc-button\": {\"background\": \"#22c55e\", \"font-size\": \"18px\", \"border-radius\": \"8px\"}}",
    "optional": true
  }
}
"""


def build_system_prompt(
    utm_source: str,
    product_title: str,
    product_description: str,
    theme_selectors: dict[str, str],
    plan_tier: str = "growth",
) -> str:
    """Construct the complete System Prompt for the LLM.

    Parameters
    ----------
    utm_source : str
        The raw UTM source value (e.g. ``tiktok_securite``).
    product_title : str
        The Shopify product title.
    product_description : str
        The Shopify product description (plain text or HTML).
    theme_selectors : dict[str, str]
        A mapping of semantic block names to the CSS selectors found on
        the page (e.g. ``{"price": ".price--large", "trust_badges": ".trust"}``).
    plan_tier : str
        The merchant's billing plan tier: "launch" (basic text+images only)
        or "growth" (full psychological restructuring).

    Returns
    -------
    str
        The complete system prompt ready to be sent to the LLM.
    """
    angle = resolve_angle(utm_source)

    # Serialise theme selectors as a readable bullet list.
    selectors_bullets = "\n".join(
        f"   - {name}: {sel}" for name, sel in theme_selectors.items()
    )

    # ── Plan-gated restrictions ──────────────────────────────────────
    if plan_tier == "launch":
        plan_restrictions = """
RESTRICTIONS DU PLAN LAUNCH (OBLIGATOIRE) :
   - Vous êtes LIMITÉ au remplacement de texte (`texts`) et d'images (`images`).
   - Le champ `structure` NE DOIT PAS apparaître dans votre réponse. Ne mettez ni `hide_elements` ni `reorder_elements`.
   - Le champ `styles` est autorisé UNIQUEMENT pour modifier la couleur de fond et la couleur de texte du bouton d'achat (`.btn--add-to-cart`). Pas de styles globaux.
"""
        allowed_schema_note = """
⚠️ ATTENTION — PLAN LAUNCH : Les champs `structure` et `styles` (sauf couleur bouton) sont INTERDITS. Votre JSON ne doit contenir que `texts` et `images`."""
    else:
        plan_restrictions = """
CAPACITÉS PLAN GROWTH (ACCÈS TOTAL) :
   - Vous avez accès à TOUS les champs : `texts`, `images`, `structure` (hide_elements + reorder_elements) et `styles`.
   - Utilisez la puissance complète de votre persona pour restructurer la page produit.
"""
        allowed_schema_note = ""

    prompt = f"""SYSTEM PROMPT — RÔLE OBLIGATOIRE

Vous êtes un {angle['persona']}, spécialiste de l'optimisation du taux de conversion (CRO) et du neuromarketing appliqué aux fiches produits Shopify.

{angle['mission']}

---

CONTEXTE PRODUIT À ANALYSER

- Titre du produit : {product_title}
- Description du produit : {product_description[:1500]}

---

SÉLECTEURS CSS DISPONIBLES SUR LA PAGE
{selectors_bullets}

---

DIRECTIVES STRATÉGIQUES

1. **Style de texte :** {angle['text_style']}

2. **Stratégie visuelle :** {angle['visual_strategy']}

{plan_restrictions}

3. **Règles absolues :**
   - Ne JAMAIS toucher au prix ni au CTA principal sauf pour forcer du CSS (champ `styles`).
   - Toujours raisonner en termes de "tunnel d'attention" : le regard du client doit glisser du titre → prix → réassurance → CTA sans rencontrer de distraction.
   - Les sélecteurs CSS que vous utilisez DOIVENT provenir de la liste fournie ci-dessus. Si un sélecteur n'existe pas, NE L'INVENTEZ PAS.
   - Si le produit n'a pas besoin d'une modification particulière dans une catégorie, OMETTEZ cette clé du JSON final (ne mettez pas de tableau vide ou de chaîne vide).
   - Maximum 4 éléments dans `hide_elements` et 2 dans `reorder_elements` pour rester focalisé.

---

FORMAT DE SORTIE OBLIGATOIRE — JSON STRICT

Votre réponse doit être UNIQUEMENT un objet JSON valide respectant EXACTEMENT le schéma ci-dessous. Aucun commentaire, aucune introduction, aucune conclusion. Juste le JSON brut.

{allowed_schema_note}

SCHÉMA ATTENDU :
{_DTR_JSON_SCHEMA}

RÈGLE ABSOLUE : Ne renvoyez RIEN d'autre que le bloc JSON. Pas de texte explicatif, pas de balises markdown ```json, uniquement le code JSON brut. Commencez votre réponse par le caractère '{{' et terminez-la par le caractère '}}'.
"""
    return prompt


# ---------------------------------------------------------------------------
# Mock / Test helpers
# ---------------------------------------------------------------------------


def mock_test() -> None:
    """Smoke-test: print a generated system prompt for manual review."""
    utm = "tiktok_securite"
    product_title = "Sac à Dos Urbain Imperméable"
    product_description = (
        "Découvrez le sac à dos qui allie style et fonctionnalité. "
        "Fabriqué en matériaux recyclés, imperméable, compartiment "
        "ordinateur 15 pouces. Livraison offerte."
    )
    theme_selectors: dict[str, str] = {
        "product_title": ".product-title",
        "product_price": ".product-price",
        "atc_button": ".btn--add-to-cart",
        "trust_badges": ".trust-badges",
        "reviews": ".reviews-summary",
        "related_products": ".related-products",
        "newsletter": ".newsletter-signup",
        "breadcrumb": ".breadcrumb",
    }

    prompt = build_system_prompt(
        utm_source=utm,
        product_title=product_title,
        product_description=product_description,
        theme_selectors=theme_selectors,
    )

    print("=" * 72)
    print(f"MOCK PROMPT FOR UTM: {utm}")
    print("=" * 72)
    print(prompt)
    print("=" * 72)
    print("END OF PROMPT")


# ---------------------------------------------------------------------------
# CLI entry point for quick validation
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mock_test()