/**
 * API Route — App Embed Activation (ScriptTag Install)
 *
 * GET /api/embed/install
 *
 * Authenticates the Shopify admin session and uses the GraphQL Admin API
 * to create a ScriptTag that injects dtr-injector.js into all product pages.
 */
import { json, type LoaderFunctionArgs, redirect } from "@remix-run/node";
import { authenticate } from "~/shopify.server";

/** The backend URL where dtr-injector.js is served as a static file. */
const DTR_BACKEND_URL =
  process.env.DTR_BACKEND_URL ?? "http://localhost:8000";

export const loader = async ({ request }: LoaderFunctionArgs) => {
  const { admin, session } = await authenticate.admin(request);

  const scriptSrc = `${DTR_BACKEND_URL}/static/dtr-injector.js`;

  // ── GraphQL mutation to create a ScriptTag ───────────────────────
  const mutation = `
    mutation scriptTagCreate($input: ScriptTagInput!) {
      scriptTagCreate(input: $input) {
        scriptTag {
          id
          src
          displayScope
        }
        userErrors {
          field
          message
        }
      }
    }
  `;

  const response = await admin.graphql(mutation, {
    variables: {
      input: {
        src: scriptSrc,
        event: "DOMContentLoaded",
        displayScope: "ALL", // Inject on every page
        cache: false,
      },
    },
  });

  const result = await response.json();

  if (result.data?.scriptTagCreate?.userErrors?.length) {
    console.error(
      "[embed.install] ScriptTag creation errors:",
      result.data.scriptTagCreate.userErrors
    );
    return json(
      {
        status: "error",
        errors: result.data.scriptTagCreate.userErrors,
      },
      { status: 400 }
    );
  }

  // Redirect back to the dashboard
  return redirect("/app");
};