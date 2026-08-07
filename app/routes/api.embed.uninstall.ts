/**
 * API Route — App Embed Deactivation (ScriptTag Uninstall)
 *
 * GET /api/embed/uninstall
 *
 * Authenticates the Shopify admin session, lists all ScriptTags, finds the
 * one pointing to dtr-injector.js, and deletes it.
 */
import { json, type LoaderFunctionArgs, redirect } from "@remix-run/cloudflare";
import { authenticate } from "~/shopify.server";

/** The backend URL where dtr-injector.js is served as a static file. */
const DTR_BACKEND_URL =
  process.env.DTR_BACKEND_URL ?? "http://localhost:8000";

export const loader = async ({ request }: LoaderFunctionArgs) => {
  const { admin, session } = await authenticate.admin(request);

  const scriptSrcMatcher = "/static/dtr-injector.js";

  try {
    // ── 1. List all ScriptTags ──────────────────────────────────────
    const listQuery = `
      query {
        scriptTags(first: 50) {
          edges {
            node {
              id
              src
            }
          }
        }
      }
    `;

    const listResponse = await admin.graphql(listQuery);
    const listResult = await listResponse.json();

    const edges = listResult.data?.scriptTags?.edges ?? [];
    const dtrTag = edges.find(
      (edge: any) => edge.node.src && edge.node.src.includes(scriptSrcMatcher)
    );

    if (!dtrTag) {
      console.warn("[embed.uninstall] No DTR ScriptTag found — nothing to delete");
      return redirect("/app");
    }

    // ── 2. Delete the ScriptTag ─────────────────────────────────────
    const deleteMutation = `
      mutation scriptTagDelete($id: ID!) {
        scriptTagDelete(id: $id) {
          deletedScriptTagId
          userErrors {
            field
            message
          }
        }
      }
    `;

    const deleteResponse = await admin.graphql(deleteMutation, {
      variables: { id: dtrTag.node.id },
    });

    const deleteResult = await deleteResponse.json();

    if (deleteResult.data?.scriptTagDelete?.userErrors?.length) {
      console.error(
        "[embed.uninstall] ScriptTag deletion errors:",
        deleteResult.data.scriptTagDelete.userErrors
      );
      return json(
        {
          status: "error",
          errors: deleteResult.data.scriptTagDelete.userErrors,
        },
        { status: 400 }
      );
    }
  } catch (err) {
    console.error("[embed.uninstall] Unexpected error:", err);
    return json(
      { status: "error", message: "Failed to uninstall ScriptTag" },
      { status: 500 }
    );
  }

  // Redirect back to the dashboard
  return redirect("/app");
};