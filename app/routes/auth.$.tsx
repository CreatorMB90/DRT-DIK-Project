/**
 * Catch-all OAuth route handler.
 *
 * Handles all Shopify OAuth callbacks:
 *   - GET  /auth/callback  → token exchange after authorization
 *   - POST /auth/token     → token refresh
 *
 * In @shopify/shopify-app-remix v3, the OAuth callback is handled
 * internally by authenticate.admin(). This route catches the auth
 * flow and returns null — Shopify takes care of the redirects.
 */

import type { LoaderFunctionArgs } from "@remix-run/cloudflare";
import shopify from "~/shopify.server";

export const loader = async ({ request }: LoaderFunctionArgs) => {
  try {
    await shopify.authenticate.admin(request);
  } catch {
    // OAuth callback or expired session — handled internally
  }
  return null;
};

export default function Auth() {
  return null;
}