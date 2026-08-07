/**
 * API Route — Shopify Billing Subscribe (Free Trial → Paid)
 *
 * GET /api/billing/subscribe?plan=9.99   → Plan Launch (14-day trial)
 * GET /api/billing/subscribe?plan=19.99  → Plan Growth (14-day trial)
 *
 * Authenticates the Shopify session, requests a recurring subscription
 * via the Shopify Billing API, and redirects the merchant to the
 * Shopify-confirmation page.
 */
import { type LoaderFunctionArgs, redirect } from "@remix-run/cloudflare";
import shopify from "~/shopify.server";

export const loader = async ({ request }: LoaderFunctionArgs) => {
  const { billing } = await shopify.authenticate.admin(request);

  const url = new URL(request.url);
  const planAmount = url.searchParams.get("plan") ?? "9.99";

  // ── Request the billing plan from Shopify ─────────────────────────
  const billingResult = (await billing.request({
    plan: planAmount,
    isTest: process.env.SHOPIFY_BILLING_TEST === "true",
    returnUrl: process.env.SHOPIFY_APP_URL
      ? `${process.env.SHOPIFY_APP_URL}/app`
      : "/app",
  })) as {
    hasActivePayment: boolean;
    confirmationUrl: string;
  };

  if (billingResult.hasActivePayment) {
    // Already subscribed — go straight to dashboard
    return redirect("/app");
  }

  // Redirect the merchant to Shopify's subscription approval page
  return redirect(billingResult.confirmationUrl);
};