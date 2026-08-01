import { vitePlugin as remix } from "@remix-run/dev";
import { defineConfig } from "vite";
import { installGlobals } from "@remix-run/node";

installGlobals();

export default defineConfig({
  plugins: [
    remix({
      appDirectory: ".",
      // Routes are auto-discovered via Remix v2 file-based conventions.
      // Existing routes:
      //   routes/app._index.tsx      → /app
      //   routes/auth.$.tsx           → /auth/*
      //   routes/auth.login.tsx       → /auth/login
      // New API routes:
      //   routes/api.optimize.ts      → /api/optimize
      //   routes/api.embed.install.ts → /api/embed/install
      //   routes/api.embed.uninstall.ts → /api/embed/uninstall
      //   routes/api.billing.subscribe.ts → /api/billing/subscribe
      //   routes/api.billing.upgrade.ts → /api/billing/upgrade
      routes(defineRoutes) {
        return defineRoutes((route) => {
          route("/app", "routes/app._index.tsx", { index: true });
          route("/auth/*", "routes/auth.$.tsx");
          route("/auth/login", "routes/auth.login.tsx");
          route("/api/optimize", "routes/api.optimize.ts");
          route("/api/embed/install", "routes/api.embed.install.ts");
          route("/api/embed/uninstall", "routes/api.embed.uninstall.ts");
          route("/api/billing/subscribe", "routes/api.billing.subscribe.ts");
          route("/api/billing/upgrade", "routes/api.billing.upgrade.ts");
        });
      },
    }),
  ],
});
