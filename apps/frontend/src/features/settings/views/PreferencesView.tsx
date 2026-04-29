"use client";

import { useTheme } from "next-themes";
import { Monitor, Moon, Sun } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  SettingsCard,
  SettingsPageHeader,
  SettingsStack,
} from "../components/SettingsPrimitives";

const THEME_OPTIONS = [
  { value: "light", label: "Light", icon: Sun },
  { value: "dark", label: "Dark", icon: Moon },
  { value: "system", label: "System", icon: Monitor },
] as const;

const ROADMAP = [
  {
    label: "Language",
    hint: "Currently English-only. Vietnamese + others queued for the i18n pass.",
  },
  {
    label: "Default LLM",
    hint: "Pre-fill the model picker for new agents — coming with the model-routing rework.",
  },
  {
    label: "Notifications",
    hint: "Email digest settings will live here once the notifications service ships.",
  },
];

export function PreferencesView() {
  const { theme, setTheme } = useTheme();

  return (
    <div>
      <SettingsPageHeader
        title="Preferences"
        description="Settings here apply everywhere you sign in."
      />

      <SettingsStack>
        <SettingsCard
          title="Appearance"
          description="Choose how the interface looks. ‘System’ follows your OS preference."
        >
          {/* Segmented control — three pills sharing the same row, much
              tighter than the previous full-card-per-option layout. */}
          <div
            role="radiogroup"
            aria-label="Theme"
            className="inline-flex rounded-lg border border-border bg-muted/30 p-1"
          >
            {THEME_OPTIONS.map((opt) => {
              const Icon = opt.icon;
              const active = theme === opt.value;
              return (
                <button
                  key={opt.value}
                  type="button"
                  role="radio"
                  aria-checked={active}
                  onClick={() => setTheme(opt.value)}
                  className={cn(
                    "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors",
                    active
                      ? "bg-background text-foreground shadow-sm"
                      : "text-muted-foreground hover:text-foreground",
                  )}
                >
                  <Icon className="h-3.5 w-3.5" />
                  {opt.label}
                </button>
              );
            })}
          </div>
        </SettingsCard>

        <SettingsCard title="Coming soon" description="Tracked on the roadmap.">
          <ul className="space-y-2.5">
            {ROADMAP.map((item) => (
              <li key={item.label} className="flex items-baseline gap-3">
                <span className="text-xs font-medium text-muted-foreground">
                  {item.label}
                </span>
                <span className="flex-1 text-[11px] text-muted-foreground/70">
                  {item.hint}
                </span>
              </li>
            ))}
          </ul>
        </SettingsCard>
      </SettingsStack>
    </div>
  );
}
