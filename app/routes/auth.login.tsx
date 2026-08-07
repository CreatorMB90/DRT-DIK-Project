/**
 * OAuth Login Entry Point
 *
 * The merchant lands here when they click "Install" from the Shopify
 * App Store or from the Partners dashboard.  This route:
 *   1. Extracts the ``shop`` query param.
 *   2. Initiates the OAuth authorization flow via ``shopifyApp``.
 *   3. Shopify redirects the merchant to accept the required scopes.
 *   4. After acceptance the callback ``/auth/callback`` handles the
 *      token exchange and redirects to the billing selection screen.
 */

import type { LoaderFunctionArgs } from "@remix-run/cloudflare";
import shopify from "~/shopify.server";

export const loader = async ({ request }: LoaderFunctionArgs) => {
  return shopify.login(request);
};

export default function Login() {
  return null;
}