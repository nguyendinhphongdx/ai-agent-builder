import { HOW_STEPS } from "../data/content";
import { Reveal } from "./Reveal";
import { Section } from "./Section";

export function HowItWorks() {
  return (
    <Section
      id="how"
      eyebrow="How it works"
      title="From clone to deployed in four steps"
      description="No staging mountain. No tutorial maze. The flow you start with is the flow you ship."
    >
      <div className="grid gap-8 md:grid-cols-2 lg:grid-cols-4">
        {HOW_STEPS.map((s, i) => (
          <Reveal key={s.step} delay={i * 100} className="relative">
            {i < HOW_STEPS.length - 1 && (
              <div
                aria-hidden="true"
                className="absolute left-[calc(100%+0.5rem)] top-8 hidden w-[calc(100%-3rem)] border-t-2 border-dashed border-border lg:block"
              />
            )}
            <div className="mb-5 flex h-16 w-16 items-center justify-center rounded-2xl border border-primary/20 bg-primary/5">
              <s.icon className="h-7 w-7 text-primary" />
            </div>
            <span className="text-xs font-bold uppercase tracking-wider text-primary">
              {s.step}
            </span>
            <h3 className="mt-2 text-lg font-bold text-foreground">{s.title}</h3>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
              {s.description}
            </p>
          </Reveal>
        ))}
      </div>
    </Section>
  );
}
