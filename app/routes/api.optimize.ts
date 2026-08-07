/**
 * API Route — AI Optimization Forwarder
 *
 * Receives the fetcher.submit from the Dashboard "Optimiser par l'IA" button,
 * authenticates the Shopify session, then forwards the request to the
 * production FastAPI backend (Render).
 *
 * POST /api/optimize
 */
import { json, type ActionFunctionArgs } from "@remix-run/cloudflare";
import { authenticate } from "~/shopify.server";

/** Backend URL — MUST point to the live Render service in production. */
const DTR_BACKEND_URL =
  process.env.DTR_BACKEND_URL ?? "http://localhost:8000";

export const action = async ({ request }: ActionFunctionArgs) => {
  // ── 1. Authenticate the Shopify admin session ──────────────────────
  const { session } = await authenticate.admin(request);

  // ── 2. Parse the incoming form data (Remix fetcher.submit) ────────
  const formData = await request.formData();

  const shop_domain = formData.get("shop_domain") as string;
  const product_id = formData.get("product_id") as string;
  const product_title = formData.get("product_title") as string;
  const product_description = (formData.get("product_description") as string) || "";
  const utm_source = formData.get("utm_source") as string;
  const plan_tier = (formData.get("plan_tier") as string) || "launch";
  const theme_selectors_raw = (formData.get("theme_selectors") as string) || "{}";

  // Basic validation
  if (!shop_domain || !product_id || !product_title || !utm_source) {
    return json(
      { status: "error", message: "Missing required fields" },
      { status: 400 }
    );
  }

  // ── 3. Forward to the Python backend (Render) ──────────────────────
  const backendUrl = `${DTR_BACKEND_URL}/api/v1/shopify/optimize`;

  try {
    const backendResponse = await fetch(backendUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Shopify-Shop-Domain": session.shop,
      },
      body: JSON.stringify({
        shop_domain,
        product_id,
        product_title,
        product_description,
        utm_source,
        plan_tier,
        theme_selectors: theme_selectors_raw,
      }),
    });

    if (!backendResponse.ok) {
      const errorBody = await backendResponse.text();
      console.error("[api.optimize] Backend error:", errorBody);
      return json(
        { status: "error", message: `Backend error: ${backendResponse.status}` },
        { status: 502 }
      );
    }

    const data = await backendResponse.json();
    return json(data);
  } catch (err) {
    console.error("[api.optimize] Network error:", err);
    return json(
      { status: "error", message: "Backend unreachable — is Render live?" },
      { status: 502 }
    );
  }
};