/**
 * Next.js calls `register()` once per server runtime at boot. We dispatch
 * to a Node or Edge Sentry init based on `NEXT_RUNTIME`. The browser SDK
 * lives in `instrumentation-client.ts` (Next 15.3+ convention).
 *
 * Empty `SENTRY_DSN` keeps the SDK fully dormant — no module-level network,
 * no breadcrumb collection — so dev/CI is unaffected.
 */
import type * as Sentry from "@sentry/nextjs";

export async function register() {
  if (!process.env.SENTRY_DSN) return;

  if (process.env.NEXT_RUNTIME === "nodejs") {
    const sentry = (await import("@sentry/nextjs")) as typeof Sentry;
    sentry.init({
      dsn: process.env.SENTRY_DSN,
      environment: process.env.SENTRY_ENVIRONMENT ?? process.env.NODE_ENV,
      release: process.env.SENTRY_RELEASE,
      // Errors only by default — bump deliberately when wanting perf data.
      tracesSampleRate: Number(process.env.SENTRY_TRACES_SAMPLE_RATE ?? 0),
      // Match backend default: never auto-attach request bodies / cookies.
      sendDefaultPii: false,
    });
  }

  if (process.env.NEXT_RUNTIME === "edge") {
    const sentry = (await import("@sentry/nextjs")) as typeof Sentry;
    sentry.init({
      dsn: process.env.SENTRY_DSN,
      environment: process.env.SENTRY_ENVIRONMENT ?? process.env.NODE_ENV,
      release: process.env.SENTRY_RELEASE,
      tracesSampleRate: Number(process.env.SENTRY_TRACES_SAMPLE_RATE ?? 0),
      sendDefaultPii: false,
    });
  }
}

// Re-thrown by Next.js's request error boundary so Sentry can capture it
// with the right runtime context. Required since Next 15.
export const onRequestError = async (
  ...args: Parameters<NonNullable<Awaited<typeof import("@sentry/nextjs")>["captureRequestError"]>>
) => {
  if (!process.env.SENTRY_DSN) return;
  const sentry = await import("@sentry/nextjs");
  return sentry.captureRequestError(...args);
};
