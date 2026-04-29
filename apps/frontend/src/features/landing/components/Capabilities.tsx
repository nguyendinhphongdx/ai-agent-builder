import { cn } from "@/lib/utils";
import { CAPABILITIES } from "../data/content";
import type { Capability } from "../data/content";
import { getVisualFor } from "./CapabilityVisuals";
import { Reveal } from "./Reveal";
import { Section } from "./Section";

export function Capabilities() {
  return (
    <Section
      id="capabilities"
      muted
      eyebrow="Capabilities"
      title={
        <>
          Everything you need to ship agents,
          <br className="hidden sm:block" /> nothing you don&apos;t.
        </>
      }
      description="Six building blocks. No plugin marketplace to maintain, no SaaS dependency to outgrow."
    >
      {/* Bento: 3-col on lg, alternates 2/1/1/2/2/1 spans for visual rhythm. */}
      <div className="mx-auto grid max-w-6xl gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {CAPABILITIES.map((cap, i) => (
          <Reveal
            key={cap.id}
            delay={i * 60}
            className={cn(
              "h-full",
              cap.span === 2 && "lg:col-span-2",
            )}
          >
            <Card cap={cap} index={i} />
          </Reveal>
        ))}
      </div>
    </Section>
  );
}

function Card({ cap, index }: { cap: Capability; index: number }) {
  const visual = getVisualFor(cap.id);
  const isWide = cap.span === 2;
  const number = String(index + 1).padStart(2, "0");

  return (
    <article
      className={cn(
        "group relative flex h-full flex-col overflow-hidden rounded-2xl border border-border bg-background p-6 shadow-sm transition-all duration-300 hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-md",
        // Wide cards become 2-column on lg: text left, visual right.
        isWide && "lg:flex-row lg:items-stretch lg:gap-8 lg:p-7",
      )}
    >
      {/* Hover glow */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 -z-10 bg-linear-to-br from-primary/0 via-transparent to-violet-500/0 opacity-0 transition-opacity duration-500 group-hover:from-primary/5 group-hover:to-violet-500/5 group-hover:opacity-100"
      />

      {/* Numbered badge — top right */}
      <span className="absolute right-5 top-5 font-mono text-[11px] font-semibold tracking-wider text-muted-foreground/60">
        {number}
      </span>

      {/* Text column */}
      <div className={cn("flex flex-col", isWide && "lg:max-w-sm lg:flex-1")}>
        <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary/10 text-primary transition-colors group-hover:bg-primary group-hover:text-primary-foreground">
          <cap.icon className="h-5 w-5" />
        </div>
        <h3 className="mt-4 text-base font-bold text-foreground sm:text-[17px]">
          {cap.title}
        </h3>
        <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
          {cap.description}
        </p>
      </div>

      {/* Visual column — sits below on narrow / mobile; right side on wide+lg */}
      {visual && (
        <div
          className={cn(
            "mt-5 flex items-end",
            isWide && "lg:mt-0 lg:flex-1 lg:items-center lg:justify-end lg:border-l lg:border-border lg:pl-8",
          )}
        >
          <div className="w-full">{visual}</div>
        </div>
      )}
    </article>
  );
}
