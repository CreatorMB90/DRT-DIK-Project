/**
 * API Route — Shopify Billing Upgrade (Launch → Growth)
 *
 * GET /api/billing/upgrade?plan=19.99
 *
 * Authenticates the Shopify session and cancels the existing Launch
 * subscription, then creates a new Growth subscription. Redirects the
 * merchant to the Shopify-confirmation page.
 */
import { type LoaderFunctionArgs, redirect } from "@remix-run/cloudflare";
import shopify from "~/shopify.server";

export const loader = async ({ request }: LoaderFunctionArgs) => {
  const { billing } = await shopify.authenticate.admin(request);

  const url = new URL(request.url);
  const planAmount = url.searchParams.get("plan") ?? "19.99";

  // ── Request the NEW billing plan from Shopify ─────────────────────
  // Shopify handles the upgrade flow: old plan is cancelled, new plan
  // starts immediately with a fresh trial period.
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
    // Already on the upgraded plan
    return redirect("/app");
  }

  // Redirect the merchant to Shopify's subscription approval page
  return redirect(billingResult.confirmationUrl);
};