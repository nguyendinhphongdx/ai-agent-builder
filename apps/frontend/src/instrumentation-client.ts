/**
 * Browser Sentry init. Loaded by Next.js on every page that hits the
 * client runtime. Empty `NEXT_PUBLIC_SENTRY_DSN` keeps the SDK dormant.
 *
 * Defaults are intentionally conservative:
 * - tracesSampleRate=0 — perf tracing off until quota is sized.
 * - replaysSessionSampleRate=0 + replaysOnErrorSampleRate=0 — Session
 *   Replay off by default (privacy + bandwidth + extra ~50KB JS).
 *   Bump deliberately if needed; consider using `mask` for PII tags.
 * - sendDefaultPii=false — matches backend; never auto-attach
 *   IPs / user-agent strings / form values without explicit opt-in.
 */
import * as Sentry from "@sentry/nextjs";

if (process.env.NEXT_PUBLIC_SENTRY_DSN) {
  Sentry.init({
    dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
    environment: process.env.NEXT_PUBLIC_SENTRY_ENVIRONMENT ?? process.env.NODE_ENV,
    release: process.env.NEXT_PUBLIC_SENTRY_RELEASE,
    tracesSampleRate: Number(process.env.NEXT_PUBLIC_SENTRY_TRACES_SAMPLE_RATE ?? 0),
    replaysSessionSampleRate: 0,
    replaysOnErrorSampleRate: 0,
    sendDefaultPii: false,
  });
}

// Required by Next.js for client-side navigation tracing instrumentation.
// Cheap no-op when the SDK is dormant.
export const onRouterTransitionStart = Sentry.captureRouterTransitionStart;
