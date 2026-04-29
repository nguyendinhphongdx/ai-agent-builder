import { Check, Minus } from "lucide-react";
import { cn } from "@/lib/utils";
import { COMPARISON_ROWS } from "../data/content";
import { Reveal } from "./Reveal";
import { Section } from "./Section";

type ColumnKey = "agentforge" | "langflow" | "dify" | "diy";

const COLUMNS: { key: ColumnKey; label: string; primary?: boolean }[] = [
  { key: "agentforge", label: "AgentForge", primary: true },
  { key: "langflow", label: "Langflow" },
  { key: "dify", label: "Dify" },
  { key: "diy", label: "DIY (LangChain only)" },
];

export function Comparison() {
  return (
    <Section
      id="compare"
      muted
      eyebrow="How we compare"
      title="Why teams pick AgentForge"
      description="Honest comparison. We genuinely like Langflow and Dify — but if you want all three ship channels, MCP, and a single docker compose up, this is where you land."
    >
      <Reveal className="mx-auto max-w-5xl overflow-hidden rounded-2xl border border-border bg-background shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-muted/40">
                <th
                  scope="col"
                  className="px-5 py-4 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground"
                >
                  Feature
                </th>
                {COLUMNS.map((c) => (
                  <th
                    key={c.key}
                    scope="col"
                    className={cn(
                      "px-5 py-4 text-center text-xs font-semibold uppercase tracking-wider",
                      c.primary ? "text-primary" : "text-muted-foreground",
                    )}
                  >
                    {c.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {COMPARISON_ROWS.map((row, idx) => (
                <tr
                  key={row.feature}
                  className={cn(
                    "border-b border-border last:border-b-0",
                    idx % 2 === 1 && "bg-muted/20",
                  )}
                >
                  <td className="px-5 py-3.5 font-medium text-foreground">
                    {row.feature}
                  </td>
                  {COLUMNS.map((c) => (
                    <td
                      key={c.key}
                      className={cn(
                        "px-5 py-3.5 text-center",
                        c.primary && "bg-primary/3",
                      )}
                    >
                      <Cell value={row[c.key]} primary={c.primary} />
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Reveal>

      <p className="mx-auto mt-6 max-w-2xl text-center text-xs text-muted-foreground">
        Last updated against published feature lists. Spotted something off?{" "}
        <a
          href="https://github.com/agentforge/agentforge/issues"
          target="_blank"
          rel="noreferrer noopener"
          className="font-medium text-foreground underline-offset-2 hover:underline"
        >
          Open an issue
        </a>{" "}
        — we&apos;ll update it.
      </p>
    </Section>
  );
}

function Cell({ value, primary }: { value: string; primary?: boolean }) {
  if (value === "yes") {
    return (
      <span
        className={cn(
          "inline-flex h-6 w-6 items-center justify-center rounded-full",
          primary ? "bg-primary text-primary-foreground" : "bg-emerald-500/15 text-emerald-500",
        )}
        aria-label="Yes"
      >
        <Check className="h-3.5 w-3.5" />
      </span>
    );
  }
  if (value === "—") {
    return (
      <span className="inline-flex h-6 w-6 items-center justify-center text-muted-foreground/60" aria-label="No">
        <Minus className="h-3.5 w-3.5" />
      </span>
    );
  }
  if (value === "partial") {
    return (
      <span
        className="inline-flex items-center rounded-full bg-amber-500/15 px-2 py-0.5 text-[11px] font-medium text-amber-600 dark:text-amber-400"
        aria-label="Partial"
      >
        partial
      </span>
    );
  }
  return <span className="text-xs font-medium text-foreground">{value}</span>;
}
