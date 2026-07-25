/**
 * DRT Extension Shopify — Frontend Injection Engine v2.0
 *
 * Injected into the <head> of a Shopify product page.  Extracts the
 * current product id, UTM source and shop domain, then fetches
 * **strictly-validated** dynamic rules from the FastAPI backend and
 * performs surgical DOM transformations:
 *
 *   1. Text replacement         (payload.texts)
 *   2. Image swap               (payload.images)
 *   3. Distraction removal      (payload.structure.hide_elements)
 *   4. Block reordering         (payload.structure.reorder_elements)
 *   5. Dynamic CSS injection    (payload.styles)
 *
 * Execution is aborted immediately when no ``utm_source`` is present,
 * ensuring zero overhead on organic / non-campaign traffic.  All DOM
 * mutations happen synchronously after the payload arrives so that
 * the visual result is painted in a single frame (CLS ≈ 0).
 */
(function () {
  "use strict";

  /* ------------------------------------------------------------------ */
  /*  1. Extract context data                                            */
  /* ------------------------------------------------------------------ */

  var host = window.location.hostname;
  // Normalise for local dev environments.
  if (!host || host === "127.0.0.1" || host === "localhost") {
    host = "string";
  }
  var shopDomain = host;
  var utmSource = new URLSearchParams(window.location.search).get(
    "utm_source"
  );
  var productId =
    (window.ShopifyAnalytics &&
      window.ShopifyAnalytics.meta &&
      window.ShopifyAnalytics.meta.product &&
      window.ShopifyAnalytics.meta.product.id) ||
    "prod_123456";

  /* ------------------------------------------------------------------ */
  /*  2. Abort immediately if no campaign UTM is present                 */
  /* ------------------------------------------------------------------ */

  if (!utmSource) {
    return;
  }

  /* ------------------------------------------------------------------ */
  /*  3. Resolve API base URL then build the fetch URL                   */
  /* ------------------------------------------------------------------ */

  // Read the backend URL from the script tag's data-api-url attribute,
  // or fall back to the same origin, or finally to localhost for dev.
  var currentScript = document.currentScript;
  var apiBase =
    (currentScript && currentScript.getAttribute("data-api-url")) ||
    (window.DTR_API_URL) ||
    (window.location.protocol + "//" + window.location.host) ||
    "http://localhost:8000";

  // Strip trailing slash if present.
  if (apiBase.charAt(apiBase.length - 1) === "/") {
    apiBase = apiBase.slice(0, -1);
  }

  var apiUrl =
    apiBase +
    "/api/v1/shopify/rules?shop_domain=" +
    encodeURIComponent(shopDomain) +
    "&product_id=" +
    encodeURIComponent(productId) +
    "&utm_source=" +
    encodeURIComponent(utmSource);

  fetch(apiUrl, {
    method: "GET",
    headers: { Accept: "application/json" },
  })
    .then(function (response) {
      if (response.status === 404) {
        return null; // No rule — do nothing
      }
      if (!response.ok) {
        return null; // Any other error — silently ignore
      }
      return response.json();
    })
    .then(function (payload) {
      if (!payload) {
        return;
      }

      console.log("[DTR] Payload reçu :", payload);

      /* -------------------------------------------------------------- */
      /*  4. Surgical DOM transformations (executed synchronously)      */
      /* -------------------------------------------------------------- */

      // ---- 4a. Text replacements ------------------------------------
      if (payload.texts && typeof payload.texts === "object") {
        Object.keys(payload.texts).forEach(function (selector) {
          try {
            var el = document.querySelector(selector);
            if (el) {
              el.textContent = payload.texts[selector];
            }
          } catch (_) {
            // Invalid CSS selector — skip silently
          }
        });
      }

      // ---- 4b. Image replacements (src + srcset) ---------------------
      if (payload.images && typeof payload.images === "object") {
        Object.keys(payload.images).forEach(function (selector) {
          try {
            var img = document.querySelector(selector);
            if (img && img.tagName === "IMG") {
              img.src = payload.images[selector];
              if (img.hasAttribute("srcset")) {
                // Remove srcset so the browser does not override our src
                img.removeAttribute("srcset");
              }
            }
          } catch (_) {
            // Invalid CSS selector — skip silently
          }
        });
      }

      // ---- 4c. Hide distracting elements -----------------------------
      if (
        payload.structure &&
        Array.isArray(payload.structure.hide_elements)
      ) {
        payload.structure.hide_elements.forEach(function (selector) {
          try {
            var el = document.querySelector(selector);
            if (el) {
              // Use style override so the element is hidden immediately
              // without triggering a layout reflow.
              el.style.setProperty("display", "none", "important");
            }
          } catch (_) {
            // Invalid CSS selector — skip silently
          }
        });
      }

      // ---- 4d. Reorder confidence blocks under the price --------------
      if (
        payload.structure &&
        Array.isArray(payload.structure.reorder_elements)
      ) {
        payload.structure.reorder_elements.forEach(function (item) {
          if (!item.element || !item.move_after) {
            return;
          }
          try {
            var moveEl = document.querySelector(item.element);
            var afterEl = document.querySelector(item.move_after);
            if (moveEl && afterEl && moveEl !== afterEl) {
              // insertAdjacentElement('afterend', ...) is a native,
              // single-pass DOM operation — no detach/append needed.
              afterEl.insertAdjacentElement("afterend", moveEl);
            }
          } catch (_) {
            // Invalid CSS selector or DOM hierarchy — skip silently
          }
        });
      }

      // ---- 4e. Dynamic CSS injection ----------------------------------
      if (payload.styles && typeof payload.styles === "object") {
        var cssRules = "";
        Object.keys(payload.styles).forEach(function (selector) {
          var props = payload.styles[selector];
          if (props && typeof props === "object") {
            var declarations = "";
            Object.keys(props).forEach(function (prop) {
              declarations +=
                prop + ": " + props[prop] + " !important; ";
            });
            if (declarations) {
              cssRules += selector + " { " + declarations + "}\n";
            }
          }
        });

        if (cssRules) {
          // Use a dedicated <style> element with a fixed id so we can
          // replace it on subsequent navigations (SPA-safe).
          var styleId = "dtr-dynamic-styles";
          var styleEl = document.getElementById(styleId);
          if (!styleEl) {
            styleEl = document.createElement("style");
            styleEl.id = styleId;
            styleEl.type = "text/css";
            document.head.appendChild(styleEl);
          }
          styleEl.textContent = cssRules;
        }
      }
    })
    .catch(function () {
      // Network error / timeout — silently ignore
    });
})();