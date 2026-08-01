/**
 * DTR Dashboard — Main merchant interface
 *
 * Features:
 *   - Welcome Banner
 *   - App Embed activation (dtr-injector.js)
 *   - Product index table with "Optimiser par l'IA" action
 *   - Plan-aware AI gating (Launch vs Growth)
 *   - Plan upgrade sidebar
 */

import { useEffect, useState, useCallback } from "react";
import { json, type LoaderFunctionArgs } from "@remix-run/node";
import { useLoaderData, useFetcher } from "@remix-run/react";
import {
  AppProvider,
  Banner,
  Button,
  Card,
  IndexTable,
  Layout,
  Link,
  Page,
  Text,
  useBreakpoints,
  Badge,
  TextStyle,
  Spinner,
  InlineStack,
  BlockStack,
  Box,
  Divider,
  Icon,
  Modal,
  Select,
  TextField,
} from "@shopify/polaris";
import { authenticate } from "~/shopify.server";

// ---------------------------------------------------------------------------
// Constants — Plan tiers
// ---------------------------------------------------------------------------

const PLAN_LAUNCH_AMOUNT = 9.99;
const PLAN_GROWTH_AMOUNT = 19.99;

type PlanTier = "launch" | "growth";

interface Product {
  id: string;
  title: string;
  status: string;
  hasRule: boolean;
  userCount: number;
}

interface LoaderData {
  activePlan: PlanTier | null;
  hasActivePayment: boolean;
  products: Product[];
  shopDomain: string;
  planAmount: number | null;
}

// ---------------------------------------------------------------------------
// Helpers — plan resolution
// ---------------------------------------------------------------------------

function resolvePlanTier(planAmount: number | undefined): PlanTier | null {
  if (!planAmount) return null;
  if (planAmount <= PLAN_LAUNCH_AMOUNT) return "launch";
  return "growth";
}

function getPlanLabel(plan: PlanTier | null): string {
  if (plan === "launch") return "Plan Launch ($9.99/mois)";
  if (plan === "growth") return "Plan Growth ($19.99/mois)";
  return "Aucun plan actif";
}

function getPlanFeatures(plan: PlanTier | null): string[] {
  if (plan === "launch") {
    return [
      "Remplacement de titre produit",
      "Remplacement d'image principale",
      "Couleur du bouton d'achat",
      "1 persona IA (CRO généraliste)",
    ];
  }
  if (plan === "growth") {
    return [
      "Restructuration Psychologique Totale",
      "Masquage des distractions (hide_elements)",
      "Déplacement des blocs de confiance (reorder_elements)",
      "5 personas IA (Urgence, Preuve Sociale, Luxe, Sécurité, Valeur)",
      "Injection CSS dynamique",
    ];
  }
  return [];
}

const PLAN_LIMITATIONS: Record<PlanTier, string[]> = {
  launch: [
    "Les fonctions de masquage (hide_elements) sont verrouillées",
    "Le réordonnancement des blocs (reorder_elements) est verrouillé",
    "Seul le persona CRO généraliste est disponible",
  ],
  growth: [],
};

// ---------------------------------------------------------------------------
// Loader — server-side data fetching
// ---------------------------------------------------------------------------

export const loader = async ({ request }: LoaderFunctionArgs) => {
  const { admin, session, billing } = await authenticate.admin(request);

  // Resolve active plan from billing
  const billingCheck = (await billing.require({
    plans: [PLAN_LAUNCH_AMOUNT.toString(), PLAN_GROWTH_AMOUNT.toString()],
    onFailure: (error: any) => {
      console.error("[DTR DASHBOARD] Billing check failed:", error);
      return { hasActivePayment: false, plan: null } as any;
    },
  })) as { hasActivePayment: boolean; appSubscriptions?: { amount: number }[] };

  let activePlan: PlanTier | null = null;
  let planAmount: number | null = null;

  if (billingCheck.hasActivePayment) {
    // Determine which plan is active
    const sub = billingCheck.appSubscriptions?.[0];
    if (sub) {
      planAmount = sub.amount;
      activePlan = resolvePlanTier(sub.amount);
    }
  }

  // Fetch products from Shopify Admin API
  let products: Product[] = [];
  try {
    const query = `
      query GetProducts($first: Int!) {
        products(first: $first) {
          edges {
            node {
              id
              title
              status
              totalInventory
            }
          }
        }
      }
    `;

    const response = await admin.graphql(query, {
      variables: { first: 50 },
    });

    const result = await response.json();
    const edges = result.data?.products?.edges ?? [];

    // Fetch DTR rules count for each product (calls our FastAPI backend)
    const dtrBaseUrl = process.env.DTR_BACKEND_URL ?? "http://localhost:8000";

    products = await Promise.all(
      edges.map(async (edge: any) => {
        const node = edge.node;
        let hasRule = false;
        let userCount = 0;

        try {
          const dtrRes = await fetch(
            `${dtrBaseUrl}/api/v1/shopify/rules/count?shop_domain=${encodeURIComponent(
              session.shop
            )}&product_id=${encodeURIComponent(
              node.id.replace("gid://shopify/Product/", "")
            )}`
          );
          if (dtrRes.ok) {
            const data = (await dtrRes.json()) as any;
            hasRule = data.count > 0;
            userCount = data.count;
          }
        } catch {
          // Backend unreachable — no rules
        }

        return {
          id: node.id.replace("gid://shopify/Product/", ""),
          title: node.title,
          status: node.status,
          hasRule,
          userCount,
        };
      })
    );
  } catch (err) {
    console.error("[DTR DASHBOARD] Failed to fetch products:", err);
    products = [];
  }

  return json<LoaderData>({
    activePlan,
    hasActivePayment: billingCheck.hasActivePayment,
    products,
    shopDomain: session.shop,
    planAmount,
  });
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function Dashboard() {
  const { activePlan, hasActivePayment, products, shopDomain, planAmount } =
    useLoaderData<typeof loader>();

  const fetcher = useFetcher();
  const [optimizingProduct, setOptimizingProduct] = useState<string | null>(
    null
  );
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedProductId, setSelectedProductId] = useState<string>("");
  const [utmSource, setUtmSource] = useState<string>("tiktok_manga");
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const planLabel = getPlanLabel(activePlan);
  const features = getPlanFeatures(activePlan);
  const limitations = activePlan ? PLAN_LIMITATIONS[activePlan] : [];

  // ── Handlers ──────────────────────────────────────────────────────────

  const handleOptimizeClick = useCallback(
    (productId: string) => {
      setSelectedProductId(productId);
      setUtmSource("tiktok_manga");
      setModalOpen(true);
    },
    []
  );

  const handleLaunchOptimization = useCallback(async () => {
    if (!selectedProductId) return;

    setOptimizingProduct(selectedProductId);
    setModalOpen(false);

    const selectedProduct = products.find((p) => p.id === selectedProductId);
    const title = selectedProduct?.title ?? "";

    fetcher.submit(
      {
        shop_domain: shopDomain,
        product_id: selectedProductId,
        product_title: title,
        product_description: "",
        utm_source: utmSource,
        plan_tier: activePlan ?? "launch",
        theme_selectors: JSON.stringify({
          product_title: ".product-title",
          product_description: ".product-description",
          product_price: ".product-price",
          atc_button: ".btn--add-to-cart",
          trust_badges: ".trust-badges",
          reviews: ".reviews-summary",
          related_products: ".related-products",
          newsletter: ".newsletter-signup",
        }),
      },
      { method: "POST", action: "/api/optimize" }
    );

    setOptimizingProduct(null);
    setToastMessage(
      `Optimisation IA lancée pour "${title}" (plan: ${planLabel}). La règle sera sauvegardée asynchrone.`
    );
    setTimeout(() => setToastMessage(null), 6000);
  }, [selectedProductId, utmSource, activePlan, shopDomain, products, fetcher, planLabel]);

  const handleUpgrade = useCallback(() => {
    // Redirect to Shopify billing upgrade URL
    const upgradeUrl = `/api/billing/upgrade?plan=${PLAN_GROWTH_AMOUNT}`;
    window.location.href = upgradeUrl;
  }, []);

  // ── Table row mapping ─────────────────────────────────────────────────

  const rowMarkup = products.map((product, index) => (
    <IndexTable.Row id={product.id} key={product.id} position={index}>
      <IndexTable.Cell>
        <TextStyle variation="strong">{product.title}</TextStyle>
      </IndexTable.Cell>
      <IndexTable.Cell>
        <Badge status={product.hasRule ? "success" : undefined}>
          {product.hasRule ? "Optimisé" : "Aucune règle"}
        </Badge>
      </IndexTable.Cell>
      <IndexTable.Cell>
        <Text as="span" variant="bodyMd">
          {product.status === "ACTIVE" ? "Actif" : "Brouillon"}
        </Text>
      </IndexTable.Cell>
      <IndexTable.Cell>
        <Button
          variant="primary"
          size="slim"
          onClick={() => handleOptimizeClick(product.id)}
          loading={optimizingProduct === product.id}
        >
          {optimizingProduct === product.id
            ? "Optimisation..."
            : "Optimiser par l'IA"}
        </Button>
      </IndexTable.Cell>
    </IndexTable.Row>
  ));

  // ── Render ────────────────────────────────────────────────────────────

  return (
    <Page
      title="Tableau de bord DTR"
      subtitle="Remplacement Dynamique de Texte — Optimisation Psychologique"
      primaryAction={{
        content: "Installer l'App Embed",
        url: "/api/embed/install",
        external: false,
      }}
    >
      <Layout>
        {/* ── MAIN CONTENT ─────────────────────────────────────────── */}
        <Layout.Section>
          <BlockStack gap="400">
            {/* Welcome Banner */}
            {!hasActivePayment && (
              <Banner title="Bienvenue sur DTR !" status="info">
                <p>
                  Activez un plan pour débloquer la puissance de l'optimisation
                  IA. Choisissez le Plan Launch (9,99 $/mois) ou le Plan Growth
                  (19,99 $/mois) avec 14 jours d'essai gratuit.
                </p>
              </Banner>
            )}

            {hasActivePayment && (
              <Banner title="DTR est actif !" status="success">
                <p>
                  Votre plan <strong>{planLabel}</strong> est actif. Vous pouvez
                  commencer à optimiser vos fiches produits.
                </p>
              </Banner>
            )}

            {/* App Embed Activation Card */}
            <Card>
              <BlockStack gap="200">
                <Text as="h2" variant="headingMd">
                  Activation du Script DTR
                </Text>
                <Text as="p" variant="bodyMd">
                  Pour que les remplacements dynamiques fonctionnent, le script{" "}
                  <code>dtr-injector.js</code> doit être injecté dans le thème
                  Shopify.
                </Text>
                <InlineStack gap="300">
                  <Button
                    variant="primary"
                    url="/api/embed/install"
                  >
                    Activer l'App Embed maintenant
                  </Button>
                  <Button
                    variant="plain"
                    url="/api/embed/uninstall"
                  >
                    Désactiver
                  </Button>
                </InlineStack>
              </BlockStack>
            </Card>

            {/* Plan Limitations Banner (Launch only) */}
            {limitations.length > 0 && (
              <Banner title="Limitations du Plan Launch" status="warning">
                <BlockStack gap="200">
                  {limitations.map((lim, i) => (
                    <Text as="p" variant="bodyMd" key={i}>
                      ⚠️ {lim}
                    </Text>
                  ))}
                  <InlineStack align="end">
                    <Button variant="primary" onClick={handleUpgrade}>
                      Passer au Plan Growth (19,99 $/mois)
                    </Button>
                  </InlineStack>
                </BlockStack>
              </Banner>
            )}

            {/* Toast notification */}
            {toastMessage && (
              <Banner status="success">
                <p>{toastMessage}</p>
              </Banner>
            )}

            {/* Product Index Table */}
            <Card>
              <BlockStack gap="400">
                <Text as="h2" variant="headingMd">
                  Produits — Optimisation IA
                </Text>
                <IndexTable
                  resourceName={{ singular: "produit", plural: "produits" }}
                  itemCount={products.length}
                  headings={[
                    { title: "Produit" },
                    { title: "Statut DTR" },
                    { title: "État Shopify" },
                    { title: "Action" },
                  ]}
                  selectable={false}
                >
                  {rowMarkup}
                </IndexTable>
                {products.length === 0 && (
                  <Box padding="400">
                    <Text as="p" variant="bodyMd" tone="subdued">
                      Aucun produit trouvé dans votre boutique.
                    </Text>
                  </Box>
                )}
              </BlockStack>
            </Card>
          </BlockStack>
        </Layout.Section>

        {/* ── SIDEBAR ──────────────────────────────────────────────── */}
        <Layout.Section variant="oneThird">
          <BlockStack gap="400">
            {/* Active Plan Card */}
            <Card>
              <BlockStack gap="300">
                <Text as="h2" variant="headingMd">
                  Votre abonnement
                </Text>
                <Badge
                  status={hasActivePayment ? "success" : "critical"}
                  size="large"
                >
                  {hasActivePayment ? planLabel : "Aucun plan"}
                </Badge>
                {hasActivePayment && planAmount && (
                  <Text as="p" variant="bodyMd">
                    {planAmount} USD / 30 jours · Essai 14 jours offert
                  </Text>
                )}
                <Divider />
                <Text as="h3" variant="headingSm">
                  Fonctionnalités incluses :
                </Text>
                <ul style={{ paddingLeft: "1.2rem", margin: 0 }}>
                  {features.map((f, i) => (
                    <li key={i}>
                      <Text as="span" variant="bodyMd">
                        {f}
                      </Text>
                    </li>
                  ))}
                </ul>
                {hasActivePayment && activePlan === "launch" && (
                  <>
                    <Divider />
                    <Button variant="primary" fullWidth onClick={handleUpgrade}>
                      Upgrade → Plan Growth (19,99 $)
                    </Button>
                    <Text as="p" variant="bodySm" tone="subdued">
                      Débloquez la restructuration psychologique totale, le
                      masquage des distractions et les 5 personas IA.
                    </Text>
                  </>
                )}
                {!hasActivePayment && (
                  <>
                    <Divider />
                    <Button
                      variant="primary"
                      fullWidth
                      url={`/api/billing/subscribe?plan=${PLAN_LAUNCH_AMOUNT}`}
                    >
                      Essayer le Plan Launch (9,99 $)
                    </Button>
                    <Button
                      variant="plain"
                      fullWidth
                      url={`/api/billing/subscribe?plan=${PLAN_GROWTH_AMOUNT}`}
                    >
                      Essayer le Plan Growth (19,99 $)
                    </Button>
                  </>
                )}
              </BlockStack>
            </Card>

            {/* Quick stats */}
            <Card>
              <BlockStack gap="200">
                <Text as="h2" variant="headingMd">
                  Statistiques rapides
                </Text>
                <Text as="p" variant="bodyMd">
                  Produits optimisés :{" "}
                  <strong>{products.filter((p) => p.hasRule).length}</strong> /{" "}
                  {products.length}
                </Text>
                <Text as="p" variant="bodyMd">
                  Plan actif : <strong>{planLabel}</strong>
                </Text>
              </BlockStack>
            </Card>
          </BlockStack>
        </Layout.Section>
      </Layout>

      {/* ── Optimization Modal ─────────────────────────────────────── */}
      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title="Lancer l'optimisation IA"
        primaryAction={{
          content: "Lancer l'optimisation",
          onAction: handleLaunchOptimization,
          disabled: !selectedProductId,
        }}
        secondaryActions={[
          {
            content: "Annuler",
            onAction: () => setModalOpen(false),
          },
        ]}
      >
        <Modal.Section>
          <BlockStack gap="400">
            <Text as="p" variant="bodyMd">
              L'IA va analyser ce produit et générer des règles de remplacement
              psychologique basées sur la source UTM.
            </Text>
            <TextField
              label="Source UTM"
              value={utmSource}
              onChange={setUtmSource}
              autoComplete="off"
              helpText={
                activePlan === "launch"
                  ? "Plan Launch : texte et image uniquement (sécurité, valeur, social)."
                  : "Plan Growth : restructuration psychologique complète."
              }
            />
            {activePlan === "launch" && (
              <Banner status="info">
                <p>
                  Avec le Plan Launch, seuls les textes et images seront
                  optimisés. Les fonctions structurelles (masquage,
                  réordonnancement) nécessitent le Plan Growth.
                </p>
              </Banner>
            )}
            <Text as="p" variant="bodySm" tone="subdued">
              Produit sélectionné :{" "}
              {products.find((p) => p.id === selectedProductId)?.title ??
                "—"}
            </Text>
          </BlockStack>
        </Modal.Section>
      </Modal>
    </Page>
  );
}

// ---------------------------------------------------------------------------
// Vercel build pipeline trigger — DTR Shopify App
// ---------------------------------------------------------------------------
