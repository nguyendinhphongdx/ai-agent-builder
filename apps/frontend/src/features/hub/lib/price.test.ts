import { describe, expect, it } from "vitest";
import { formatPrice, priceMajorUnits, providerForCurrency } from "./price";

describe("priceMajorUnits", () => {
  it("divides by 100 for cent-based currencies", () => {
    expect(priceMajorUnits(999, "USD")).toBe(9.99);
    expect(priceMajorUnits(100, "EUR")).toBe(1);
  });

  it("treats price_cents as whole units for VND", () => {
    expect(priceMajorUnits(50000, "VND")).toBe(50000);
    expect(priceMajorUnits(199_000, "VND")).toBe(199_000);
  });

  it("treats price_cents as whole units for JPY/KRW", () => {
    expect(priceMajorUnits(500, "JPY")).toBe(500);
    expect(priceMajorUnits(1_000, "KRW")).toBe(1_000);
  });

  it("is case-insensitive", () => {
    expect(priceMajorUnits(50000, "vnd")).toBe(50000);
  });
});

describe("formatPrice", () => {
  it("returns 'Free' for zero / negative", () => {
    expect(formatPrice(0, "USD")).toBe("Free");
    expect(formatPrice(-1, "USD")).toBe("Free");
  });

  it("formats USD with two decimals", () => {
    expect(formatPrice(999, "USD")).toMatch(/\$9\.99/);
  });

  it("formats VND without decimals using vi-VN locale", () => {
    const formatted = formatPrice(50_000, "VND");
    // vi-VN format: "50.000 ₫" — `.` is the thousands separator,
    // `,` would be the decimal separator (which we don't want).
    expect(formatted).toContain("50");
    expect(formatted).toContain("₫");
    expect(formatted).not.toMatch(/,\d{2}/);
  });

  it("falls back to a readable label for unknown currencies", () => {
    expect(formatPrice(100, "XYZ")).toMatch(/XYZ/);
  });

  it("defaults to USD when currency is null", () => {
    expect(formatPrice(500, null)).toMatch(/\$5\.00/);
  });
});

describe("providerForCurrency", () => {
  it("routes VND to MoMo", () => {
    expect(providerForCurrency("VND")).toBe("momo");
    expect(providerForCurrency("vnd")).toBe("momo");
  });

  it("routes everything else to Stripe", () => {
    expect(providerForCurrency("USD")).toBe("stripe");
    expect(providerForCurrency("EUR")).toBe("stripe");
  });
});
