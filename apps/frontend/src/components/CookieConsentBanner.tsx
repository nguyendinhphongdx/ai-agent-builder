"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

/**
 * Cookie consent banner — VN compliance (Nghị định 13/2023).
 *
 * Shows once until the visitor picks "Accept all" or "Essential only".
 * We don't actually load any non-essential cookies right now, but the
 * banner is needed today to be ready for analytics/marketing tomorrow
 * and to honour the consent-required principle.
 *
 * Choice is persisted to localStorage so it survives navigation but
 * not "Clear site data". A 365-day cookie clone would be more
 * lawful-bound but the practical UX difference is minor — easy to
 * upgrade later if a DPA pushes back.
 */
const STORAGE_KEY = "agentforge:cookie-consent";
type Consent = "accepted" | "essential-only";

function getStored(): Consent | null {
  if (typeof window === "undefined") return null;
  const v = window.localStorage.getItem(STORAGE_KEY);
  return v === "accepted" || v === "essential-only" ? v : null;
}

export function CookieConsentBanner() {
  // ``null`` = haven't checked yet (SSR / first paint). The first
  // effect either hides the banner or shows it; we render nothing
  // during the in-between to avoid a flash on subsequent navigations.
  const [state, setState] = useState<Consent | "show" | null>(null);

  useEffect(() => {
    setState(getStored() ?? "show");
  }, []);

  if (state !== "show") return null;

  const choose = (choice: Consent) => {
    try {
      window.localStorage.setItem(STORAGE_KEY, choice);
    } catch {
      // private mode / quota — banner will reappear, acceptable.
    }
    setState(choice);
  };

  return (
    <div
      role="dialog"
      aria-label="Cookie consent"
      className="fixed inset-x-3 bottom-3 z-50 mx-auto max-w-3xl rounded-lg border border-border bg-background/95 p-4 shadow-lg backdrop-blur md:inset-x-auto md:left-1/2 md:-translate-x-1/2"
    >
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:gap-5">
        <div className="flex-1 text-xs leading-relaxed text-muted-foreground">
          Chúng tôi dùng cookie cần thiết để giữ phiên đăng nhập và bảo mật. Hiện
          chưa có cookie analytics/marketing — nếu sau này có, bạn sẽ được hỏi
          trước. Đọc thêm tại{" "}
          <Link href="/cookies" className="text-foreground underline">
            Chính sách Cookie
          </Link>
          {" "}và{" "}
          <Link href="/privacy" className="text-foreground underline">
            Chính sách Bảo mật
          </Link>
          .
        </div>
        <div className="flex shrink-0 gap-2">
          <button
            type="button"
            onClick={() => choose("essential-only")}
            className="rounded-md border border-border px-3 py-1.5 text-xs hover:bg-accent"
          >
            Chỉ cần thiết
          </button>
          <button
            type="button"
            onClick={() => choose("accepted")}
            className="rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground hover:bg-primary/90"
          >
            Đồng ý tất cả
          </button>
        </div>
      </div>
    </div>
  );
}
