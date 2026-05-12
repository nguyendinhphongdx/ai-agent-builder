// Bundled at build time — keeps client bundle small for the two
// languages we ship MVP. Add more locales by importing here and
// registering in ``LOCALES``. Mainstream next-intl can drop in
// later without touching call sites if we keep the API the same.
import en from "../../../messages/en.json";
import vi from "../../../messages/vi.json";

export type Locale = "en" | "vi";

export const LOCALES: Locale[] = ["en", "vi"];

export const DEFAULT_LOCALE: Locale = "en";

// Type the dict from the canonical EN source so missing keys in
// other locales fall back without breaking compile.
export type Messages = typeof en;

export const MESSAGES: Record<Locale, Messages> = {
  en: en as Messages,
  vi: vi as Messages,
};

// Browser cookie name. Server (Next.js middleware) and client both
// read this to settle on the active locale; users can override via
// the LocaleSwitcher.
export const LOCALE_COOKIE = "agentforge_locale";
