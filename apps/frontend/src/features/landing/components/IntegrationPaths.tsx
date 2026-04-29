"use client";

import { useState } from "react";
import { ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";
import { INTEGRATION_PATHS } from "../data/content";
import { MonacoCodeBlock } from "./MonacoCodeBlock";
import { Reveal } from "./Reveal";
import { Section } from "./Section";

export function IntegrationPaths() {
  const [activeId, setActiveId] = useState<string>(INTEGRATION_PATHS[0].id);
  const active =
    INTEGRATION_PATHS.find((p) => p.id === activeId) ?? INTEGRATION_PATHS[0];

  return (
    <Section
      id="integrate"
      eyebrow="Integrate"
      title={
        <>
          One agent, three channels.
          <br className="hidden sm:block" /> Pick whichever fits.
        </>
      }
      description="Most platforms give you a chat window. AgentForge gives you the agent — embed it on a site, call it over REST, or wire it into Claude Desktop."
    >
      <Reveal className="mx-auto max-w-5xl">
        {/* Tab cards — 3 across on md+, stacked on mobile */}
        <div role="tablist" className="grid gap-3 md:grid-cols-3">
          {INTEGRATION_PATHS.map((p) => {
            const isActive = p.id === activeId;
            return (
              <button
                key={p.id}
                type="button"
                role="tab"
                aria-selected={isActive}
                aria-controls="integration-code-panel"
                onClick={() => setActiveId(p.id)}
                className={cn(
                  "group relative flex items-start gap-3 rounded-xl border p-4 text-left transition-all",
                  isActive
                    ? "border-primary bg-primary/5 shadow-sm"
                    : "border-border bg-background hover:border-primary/30 hover:bg-muted/40",
                )}
              >
                <div
                  className={cn(
                    "flex h-9 w-9 shrink-0 items-center justify-center rounded-lg transition-colors",
                    isActive
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted text-muted-foreground group-hover:bg-primary/10 group-hover:text-primary",
                  )}
                >
                  <p.icon className="h-4 w-4" />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-foreground">
                      {p.title}
                    </span>
                  </div>
                  <p className="mt-0.5 text-xs text-muted-foreground">{p.tagline}</p>
                </div>
                {/* Active indicator dot */}
                <span
                  aria-hidden="true"
                  className={cn(
                    "mt-1 h-2 w-2 shrink-0 rounded-full transition-colors",
                    isActive ? "bg-primary" : "bg-transparent",
                  )}
                />
              </button>
            );
          })}
        </div>

        {/* Active path pitch — bridges tabs and editor */}
        <div
          id="integration-code-panel"
          role="tabpanel"
          aria-labelledby={`tab-${active.id}`}
          className="mt-6"
        >
          <div className="mb-3 flex items-start gap-2 text-sm text-muted-foreground">
            <ArrowRight className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
            <p className="leading-relaxed">{active.pitch}</p>
          </div>

          <MonacoCodeBlock path={active} />
        </div>
      </Reveal>
    </Section>
  );
}
