import { TRUST_LOGOS } from "../data/content";

export function TrustBar() {
  return (
    <section className="border-t border-border bg-muted/30">
      <div className="mx-auto max-w-7xl px-6 py-12 lg:px-8">
        <p className="text-center text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground">
          Built on the stack you already trust
        </p>
        <div className="mt-8 grid grid-cols-2 gap-x-8 gap-y-6 sm:grid-cols-4 lg:grid-cols-8">
          {TRUST_LOGOS.map((l) => (
            <div
              key={l.name}
              className="flex flex-col items-center text-center transition-opacity hover:opacity-100 sm:opacity-70"
            >
              <div className="text-sm font-semibold tracking-tight text-foreground">
                {l.name}
              </div>
              <div className="mt-0.5 text-[11px] text-muted-foreground">{l.sub}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
