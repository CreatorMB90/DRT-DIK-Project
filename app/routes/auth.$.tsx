/**
 * Catch-all OAuth route handler.
 *
 * Handles all Shopify OAuth callbacks:
 *   - GET  /auth/callback  → token exchange after authorization
 *   - POST /auth/token     → token refresh
 */

import type { LoaderFunctionArgs } from "@remix-run/node";
import shopify from "~/shopify.server";

export const loader = async ({ request }: LoaderFunctionArgs) => {
  return shopify.authenticate.admin(request).then(
    () => null,
    () => shopify.auth.callback(request)
  );
};

export default function Auth() {
  return null;
}