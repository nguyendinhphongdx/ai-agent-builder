"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import {
  DEFAULT_LOCALE,
  LOCALES,
  LOCALE_COOKIE,
  MESSAGES,
  type Locale,
  type Messages,
} from "./messages";

interface I18nContextValue {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: (key: string) => string;
}

const I18nContext = createContext<I18nContextValue | null>(null);

/**
 * Minimal-deps i18n provider — read locale from cookie at mount,
 * persist on change. Translation lookup is dot-path
 * ("settings.account") into the loaded JSON.
 *
 * Why not next-intl directly: MVP. next-intl needs locale-prefixed
 * routes ([locale] segment) or middleware-driven rewrites. Both
 * are larger refactors than we want for this slice. Migrating
 * later is a drop-in if we keep the ``t(key)`` API stable.
 */
export function I18nProvider({
  initialLocale = DEFAULT_LOCALE,
  children,
}: {
  initialLocale?: Locale;
  children: React.ReactNode;
}) {
  const [locale, setLocaleState] = useState<Locale>(initialLocale);

  // Hydrate from cookie on first client render. Server-side we
  // can't read it without middleware, so this is a one-frame flash
  // for users who picked a non-default locale. Acceptable for MVP.
  useEffect(() => {
    const cookies = document.cookie.split("; ");
    const found = cookies
      .find((c) => c.startsWith(`${LOCALE_COOKIE}=`))
      ?.split("=")[1];
    if (found && LOCALES.includes(found as Locale) && found !== locale) {
      setLocaleState(found as Locale);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const setLocale = useCallback((next: Locale) => {
    setLocaleState(next);
    // Year-long cookie. Same-site Lax so OAuth callbacks preserve it.
    document.cookie = `${LOCALE_COOKIE}=${next}; path=/; max-age=${60 * 60 * 24 * 365}; SameSite=Lax`;
  }, []);

  const t = useMemo(() => {
    const dict = MESSAGES[locale];
    return (key: string): string => {
      // Walk dot-path; fall back to the key itself if missing so a
      // typo'd key shows up obviously in dev rather than rendering
      // empty.
      const parts = key.split(".");
      let cursor: unknown = dict as Messages;
      for (const p of parts) {
        if (cursor && typeof cursor === "object" && p in cursor) {
          cursor = (cursor as Record<string, unknown>)[p];
        } else {
          return key;
        }
      }
      return typeof cursor === "string" ? cursor : key;
    };
  }, [locale]);

  const value = useMemo(() => ({ locale, setLocale, t }), [locale, setLocale, t]);

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useTranslations() {
  const ctx = useContext(I18nContext);
  if (!ctx) {
    throw new Error("useTranslations must be inside <I18nProvider />");
  }
  return ctx;
}
