/**
 * Shopify App Server Configuration
 *
 * Handles OAuth, session storage, webhooks, and — most importantly —
 * Billing (recurring subscription plans).
 */

import { shopifyApp, BillingInterval } from "@shopify/shopify-app-remix/server";
import { PrismaSessionStorage } from "@shopify/shopify-app-session-storage-prisma";
import { PrismaClient } from "@prisma/client";

// ---------------------------------------------------------------------------
// Database-backed session storage (production-grade)
// ---------------------------------------------------------------------------
const prisma = new PrismaClient();

const sessionStorage = new PrismaSessionStorage(prisma);

// ---------------------------------------------------------------------------
// Plan definitions — two performance-gated tiers
// ---------------------------------------------------------------------------

/**
 * PLAN LAUNCH — $9.99 USD / month (14-day free trial)
 *
 * Capabilities:
 *   • Text replacement (title, description)
 *   • Image swap (main product image)
 *   • Button color styling
 *
 * Restriction:
 *   • ``hide_elements`` and ``reorder_elements`` are DISABLED.
 *   • Only 1 AI persona (default CRO expert).
 */
const PLAN_LAUNCH = {
  amount: 9.99,
  currencyCode: "USD",
  interval: BillingInterval.Every30Days,
  trialDays: 14,
};

/**
 * PLAN GROWTH — $19.99 USD / month (14-day free trial)
 *
 * Capabilities:
 *   • Full psychological restructuring.
 *   • Distraction hiding (hide_elements).
 *   • Confidence-block reordering (reorder_elements).
 *   • All 5 AI personas (Urgency, Social Proof, Luxury, Security, Value).
 */
const PLAN_GROWTH = {
  amount: 19.99,
  currencyCode: "USD",
  interval: BillingInterval.Every30Days,
  trialDays: 14,
};

// ---------------------------------------------------------------------------
// shopifyApp() instance — exported as the single source of truth
// ---------------------------------------------------------------------------

export const MONTHLY_PLANS = [PLAN_LAUNCH, PLAN_GROWTH];

const shopify = shopifyApp({
  apiKey: process.env.SHOPIFY_API_KEY!,
  apiSecretKey: process.env.SHOPIFY_API_SECRET!,
  scopes: [
    "write_products",
    "read_products",
    "write_themes",
    "read_themes",
    "write_script_tags",
    "read_script_tags",
  ],
  appUrl: process.env.SHOPIFY_APP_URL!,
  sessionStorage,
  billing: {
    [PLAN_LAUNCH.amount.toString()]: {
      amount: PLAN_LAUNCH.amount,
      currencyCode: PLAN_LAUNCH.currencyCode,
      interval: PLAN_LAUNCH.interval,
      trialDays: PLAN_LAUNCH.trialDays,
    },
    [PLAN_GROWTH.amount.toString()]: {
      amount: PLAN_GROWTH.amount,
      currencyCode: PLAN_GROWTH.currencyCode,
      interval: PLAN_GROWTH.interval,
      trialDays: PLAN_GROWTH.trialDays,
    },
  },
  // Automatically redirect to billing page if no active subscription
  billingCheck: async ({ session, billing }) => {
    const plans = await billing.require({
      plans: [
        PLAN_LAUNCH.amount.toString(),
        PLAN_GROWTH.amount.toString(),
      ],
      onFailure: (error) => {
        console.error("[BILLING] Failed to verify subscription:", error);
        throw error;
      },
    });

    const activePlan = plans.hasActivePayment
      ? plans.oneTimePurchases?.[0] || plans.appSubscriptions?.[0]
      : null;

    return {
      hasPayment: plans.hasActivePayment,
      plan: activePlan
        ? {
            name: activePlan.name,
            amount: activePlan.amount,
            currencyCode: activePlan.currencyCode,
          }
        : null,
    };
  },
});

export default shopify;
export const authenticate = shopify.authenticate;