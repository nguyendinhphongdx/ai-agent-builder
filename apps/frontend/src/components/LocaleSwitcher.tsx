"use client";

import { Globe } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useTranslations } from "@/lib/i18n/context";
import { LOCALES, type Locale } from "@/lib/i18n/messages";

const LABELS: Record<Locale, string> = {
  en: "English",
  vi: "Tiếng Việt",
};

/**
 * Header-level language switcher. Sets the locale cookie so SSR
 * picks it up on the next page load (full-page navigation = fresh
 * server bundle, no need to re-route per next-intl).
 */
export function LocaleSwitcher() {
  const { locale, setLocale, t } = useTranslations();
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          type="button"
          className="inline-flex h-8 items-center gap-1.5 rounded-md px-2 text-[11px] text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
          aria-label={t("common.language")}
        >
          <Globe className="h-3.5 w-3.5" />
          <span className="font-medium uppercase">{locale}</span>
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-40">
        {LOCALES.map((l) => (
          <DropdownMenuItem
            key={l}
            onClick={() => setLocale(l)}
            className={l === locale ? "font-medium" : ""}
          >
            {LABELS[l]}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
