import { vitePlugin as remix } from "@remix-run/dev";
import { defineConfig } from "vite";
import { installGlobals } from "@remix-run/node";

installGlobals();

export default defineConfig({
  plugins: [
    remix({
      // Routes are in app/routes/ (already contains the dashboard)
      routes(defineRoutes) {
        return defineRoutes((route) => {
          route("/app", "routes/app._index.tsx", { index: true });
          route("/auth/*", "routes/auth.$.tsx");
          route("/auth/login", "routes/auth.login.tsx");
        });
      },
    }),
  ],
});