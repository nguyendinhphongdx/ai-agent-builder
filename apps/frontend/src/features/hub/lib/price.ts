/**
 * Price helpers for Hub templates.
 *
 * The backend stores `price_cents` as an integer in each currency's
 * smallest unit. For most currencies that's literally cents (USD, EUR,
 * GBP — divide by 100 to display); for VND, MoMo treats the integer as
 * whole đồng (don't divide). The column name is a misnomer for VND but
 * we preserve it to avoid a churn-only schema migration.
 */

const SUBUNIT_DIVISOR: Record<string, number> = {
  // Currencies without decimals — `price_cents` is already the
  // displayable whole-unit amount.
  VND: 1,
  JPY: 1,
  KRW: 1,
};

/** Provider canonical id matching `Purchase.provider` on the backend. */
export type PaymentProvider = "stripe" | "momo";

/** Currencies the frontend explicitly knows how to charge in. The
 *  backend dispatches to MoMo for VND and Stripe for everything else,
 *  but the UI doesn't enumerate every Stripe-supported currency — pick
 *  from these in PublishDialog and let backend reject the rest. */
export const SUPPORTED_CURRENCIES = ["USD", "VND"] as const;
export type Currency = (typeof SUPPORTED_CURRENCIES)[number];

/** Whole-unit value (e.g. dollars, đồng) given a `price_cents` integer. */
export function priceMajorUnits(priceCents: number, currency: string): number {
  const divisor = SUBUNIT_DIVISOR[currency.toUpperCase()] ?? 100;
  return priceCents / divisor;
}

/** Currency-aware price label. Falls back to USD formatting for unknown
 *  currencies — better than throwing in a render path. */
export function formatPrice(priceCents: number, currency: string | null | undefined): string {
  if (priceCents <= 0) return "Free";
  const cur = (currency || "USD").toUpperCase();
  const divisor = SUBUNIT_DIVISOR[cur] ?? 100;
  const minimumFractionDigits = divisor === 1 ? 0 : 2;
  // Use vi-VN for VND so the formatter inserts the đ symbol the way
  // Vietnamese readers expect (e.g. "9.999 ₫" instead of "VND 9,999.00").
  const locale = cur === "VND" ? "vi-VN" : "en-US";
  try {
    return new Intl.NumberFormat(locale, {
      style: "currency",
      currency: cur,
      minimumFractionDigits,
      maximumFractionDigits: minimumFractionDigits,
    }).format(priceCents / divisor);
  } catch {
    // Unknown currency code — render the integer with the code as a suffix.
    return `${priceCents / divisor} ${cur}`;
  }
}

/** Map a frontend currency choice to the provider that will handle it. */
export function providerForCurrency(currency: string): PaymentProvider {
  return currency.toUpperCase() === "VND" ? "momo" : "stripe";
}
