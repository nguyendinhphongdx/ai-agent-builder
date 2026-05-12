"use client";

import { useQuery } from "@tanstack/react-query";
import { Download, ThumbsDown, ThumbsUp } from "lucide-react";
import {
  SettingsCard,
  SettingsPageHeader,
  SettingsStack,
} from "@/features/settings/components/SettingsPrimitives";
import { cn } from "@/lib/utils";
import { annotationsService } from "@/lib/api/annotationsService";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

/**
 * Quality dashboard fed by message thumbs up/down.
 *
 * Three sections:
 *   - Totals row (up / down / total / rate%).
 *   - Top failure tags (when users tag their thumbs-downs).
 *   - Recent thumbs-down list — links back to the message in
 *     chat so reviewers can read the failed turn in context.
 *   - Two export buttons: full JSONL + thumbs-down-only "gold"
 *     JSONL for fine-tuning.
 */
export function AnnotationsView() {
  const totals = useQuery({
    queryKey: ["ann-totals"],
    queryFn: () => annotationsService.totals(),
  });
  const tags = useQuery({
    queryKey: ["ann-tags"],
    queryFn: () => annotationsService.topTags(10),
  });
  const recent = useQuery({
    queryKey: ["ann-recent-negative"],
    queryFn: () => annotationsService.recentNegative(20),
  });

  return (
    <div className="mx-auto max-w-5xl p-6">
      <SettingsPageHeader
        title="Quality & Feedback"
        description="Thumbs up/down ratings from your conversations. Use them to spot regressions and export a fine-tuning dataset."
        action={
          <div className="flex gap-2">
            <a
              href={`${API_BASE}/annotations/export.jsonl`}
              className="inline-flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-xs font-medium hover:bg-accent"
              download
            >
              <Download className="h-3 w-3" /> All as JSONL
            </a>
            <a
              href={`${API_BASE}/annotations/export.jsonl?only_negative=true`}
              className="inline-flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground hover:bg-primary/90"
              download
            >
              <Download className="h-3 w-3" /> Gold corpus
            </a>
          </div>
        }
      />

      <SettingsStack>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <StatCard
            icon={ThumbsUp}
            label="Thumbs up"
            value={totals.data?.up.toLocaleString() ?? "—"}
            tone="emerald"
          />
          <StatCard
            icon={ThumbsDown}
            label="Thumbs down"
            value={totals.data?.down.toLocaleString() ?? "—"}
            tone="rose"
          />
          <StatCard
            label="Total ratings"
            value={totals.data?.total.toLocaleString() ?? "—"}
          />
          <StatCard
            label="Up rate"
            value={
              totals.data
                ? `${(totals.data.up_rate * 100).toFixed(1)}%`
                : "—"
            }
            tone={
              totals.data && totals.data.up_rate < 0.7 ? "rose" : "emerald"
            }
          />
        </div>

        <SettingsCard title="Top failure tags" description="Where users say it went wrong.">
          {(tags.data ?? []).length === 0 ? (
            <p className="px-5 py-6 text-xs text-muted-foreground">
              No tagged feedback yet. Encourage reviewers to tag their thumbs-down.
            </p>
          ) : (
            <ul className="divide-y divide-border">
              {(tags.data ?? []).map((t) => (
                <li
                  key={t.tag}
                  className="flex items-center justify-between px-5 py-2 text-xs"
                >
                  <span className="font-mono">{t.tag}</span>
                  <span className="tabular-nums text-muted-foreground">
                    {t.count}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </SettingsCard>

        <SettingsCard title="Recent thumbs-down" description="Newest first. Click a row to see the feedback.">
          {(recent.data ?? []).length === 0 ? (
            <p className="px-5 py-6 text-xs text-muted-foreground">
              Nothing flagged recently — nice work.
            </p>
          ) : (
            <ul className="divide-y divide-border">
              {(recent.data ?? []).map((a) => (
                <li key={a.id} className="px-5 py-3">
                  <div className="flex items-baseline justify-between gap-2">
                    <span className="font-mono text-[11px] text-muted-foreground">
                      {new Date(a.created_at).toLocaleString()}
                    </span>
                    <span className="font-mono text-[10px] text-muted-foreground/70">
                      msg {a.message_id.slice(0, 8)}
                    </span>
                  </div>
                  {a.feedback && (
                    <p className="mt-1 text-[12px] text-foreground">{a.feedback}</p>
                  )}
                  {a.expected_response && (
                    <p className="mt-1 rounded-md bg-emerald-500/10 px-2 py-1 text-[11px] text-emerald-700 dark:text-emerald-300">
                      ✓ Expected: {a.expected_response}
                    </p>
                  )}
                  {a.tags.length > 0 && (
                    <div className="mt-1 flex flex-wrap gap-1">
                      {a.tags.map((t) => (
                        <span
                          key={t}
                          className="rounded-full bg-muted/60 px-2 py-0.5 text-[10px] font-mono"
                        >
                          {t}
                        </span>
                      ))}
                    </div>
                  )}
                </li>
              ))}
            </ul>
          )}
        </SettingsCard>
      </SettingsStack>
    </div>
  );
}

function StatCard({
  icon: Icon,
  label,
  value,
  tone,
}: {
  icon?: React.ElementType;
  label: string;
  value: string;
  tone?: "emerald" | "rose";
}) {
  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <div className="flex items-center justify-between">
        <span className="text-[11px] font-medium text-muted-foreground">{label}</span>
        {Icon && (
          <Icon
            className={cn(
              "h-3 w-3",
              tone === "emerald" && "text-emerald-500",
              tone === "rose" && "text-rose-500",
            )}
          />
        )}
      </div>
      <div
        className={cn(
          "mt-1 text-xl font-semibold",
          tone === "rose" && "text-rose-600",
          tone === "emerald" && "text-emerald-600",
        )}
      >
        {value}
      </div>
    </div>
  );
}
