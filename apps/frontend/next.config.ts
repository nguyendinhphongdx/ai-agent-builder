import type { NextConfig } from "next";
import { withSentryConfig } from "@sentry/nextjs";

const nextConfig: NextConfig = {
  // Produce a self-contained server bundle in `.next/standalone/` so the
  // production Docker image stays small (~150MB vs full node_modules copy).
  output: "standalone",
};

// `withSentryConfig` injects the Sentry webpack plugin, which uploads
// source maps to Sentry at build time. Without it, stack traces in the
// Sentry UI would show minified function names. The plugin is a no-op
// unless `SENTRY_AUTH_TOKEN` (and `SENTRY_ORG` / `SENTRY_PROJECT`) are
// set — typical pattern is to provide these only in CI/CD.
export default withSentryConfig(nextConfig, {
  org: process.env.SENTRY_ORG,
  project: process.env.SENTRY_PROJECT,
  // Auth token is read from `SENTRY_AUTH_TOKEN` automatically.
  silent: !process.env.CI,
  // Strip source maps from the client bundle after upload — the symbol
  // lookup runs server-side at Sentry, the browser doesn't need them.
  sourcemaps: { deleteSourcemapsAfterUpload: true },
  disableLogger: true,
  widenClientFileUpload: true,
});
