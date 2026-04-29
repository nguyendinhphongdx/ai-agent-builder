"use client";

import { useTheme } from "next-themes";
import { Monitor, Moon, Sun } from "lucide-react";
import { cn } from "@/lib/utils";

/** App-wide preferences. Theme is currently the only one wired; future
 *  preferences (language, default LLM, notifications) join this page. */
export function PreferencesView() {
  return (
    <section className="space-y-8">
      <header>
        <h1 className="font-heading text-xl font-semibold">Preferences</h1>
        <p className="mt-1 text-xs text-muted-foreground">
          Choose how the app looks and behaves. Settings here apply everywhere
          you sign in.
        </p>
      </header>

      <ThemeSection />
      <ComingSoonSection />
    </section>
  );
}

function ThemeSection() {
  const { theme, setTheme } = useTheme();

  const choices: { value: string; label: string; icon: React.ElementType; hint: string }[] = [
    {
      value: "light",
      label: "Light",
      icon: Sun,
      hint: "High contrast, daytime use.",
    },
    {
      value: "dark",
      label: "Dark",
      icon: Moon,
      hint: "Lower glare, kinder at night.",
    },
    {
      value: "system",
      label: "System",
      icon: Monitor,
      hint: "Follow your OS preference.",
    },
  ];

  return (
    <div>
      <h2 className="mb-3 text-sm font-semibold">Appearance</h2>
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
        {choices.map((c) => {
          const Icon = c.icon;
          const active = theme === c.value;
          return (
            <button
              key={c.value}
              type="button"
              onClick={() => setTheme(c.value)}
              className={cn(
                "flex items-start gap-3 rounded-xl border p-4 text-left transition-colors",
                active
                  ? "border-primary bg-primary/5"
                  : "border-border bg-card hover:border-foreground/30",
              )}
            >
              <Icon
                className={cn(
                  "mt-0.5 h-4 w-4 shrink-0",
                  active ? "text-primary" : "text-muted-foreground",
                )}
              />
              <div className="flex-1">
                <p className="text-sm font-medium">{c.label}</p>
                <p className="mt-0.5 text-[11px] text-muted-foreground">{c.hint}</p>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}

function ComingSoonSection() {
  // Placeholder so users can see the roadmap. Hook these into real state
  // when the backing features land (not a stub today).
  const items: { label: string; hint: string }[] = [
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
  return (
    <div>
      <h2 className="mb-3 text-sm font-semibold">Coming soon</h2>
      <ul className="space-y-2">
        {items.map((it) => (
          <li
            key={it.label}
            className="flex items-start gap-3 rounded-xl border border-dashed border-border bg-muted/20 p-3"
          >
            <div className="flex-1">
              <p className="text-xs font-medium text-muted-foreground">{it.label}</p>
              <p className="mt-0.5 text-[11px] text-muted-foreground/70">{it.hint}</p>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
