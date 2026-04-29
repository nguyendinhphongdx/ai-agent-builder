"use client";

import { useState } from "react";
import Link from "next/link";
import { Loader2, Sparkles, Star } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAdminTemplates, useModerateTemplate } from "../hooks/useAdmin";
import type { AdminTemplateRow } from "../types";

const STATUS_FILTERS = [
  { value: "", label: "All" },
  { value: "published", label: "Published" },
  { value: "draft", label: "Draft" },
  { value: "suspended", label: "Suspended" },
  { value: "archived", label: "Archived" },
];

export function TemplatesTab() {
  const [filter, setFilter] = useState({ status: "", q: "" });
  const { data: templates, isLoading } = useAdminTemplates({
    status: filter.status || undefined,
    q: filter.q || undefined,
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Input
          value={filter.q}
          onChange={(e) => setFilter({ ...filter, q: e.target.value })}
          placeholder="Search title..."
          className="max-w-xs text-xs"
        />
        <div className="flex gap-1">
          {STATUS_FILTERS.map((s) => (
            <button
              key={s.value}
              onClick={() => setFilter({ ...filter, status: s.value })}
              className={`rounded-full border px-2.5 py-1 text-[11px] transition-colors ${
                filter.status === s.value
                  ? "border-violet-500 bg-violet-500 text-white"
                  : "border-border text-muted-foreground hover:bg-accent"
              }`}
            >
              {s.label}
            </button>
          ))}
        </div>
      </div>

      {isLoading ? (
        <Loader />
      ) : !templates || templates.length === 0 ? (
        <Empty />
      ) : (
        <div className="space-y-2">
          {templates.map((t) => (
            <TemplateRow key={t.id} template={t} />
          ))}
        </div>
      )}
    </div>
  );
}

function TemplateRow({ template }: { template: AdminTemplateRow }) {
  const moderate = useModerateTemplate();

  const toggleFeatured = () =>
    moderate.mutate({ id: template.id, body: { is_featured: !template.is_featured } });

  const setStatus = (status: AdminTemplateRow["status"]) => {
    if (
      status === "suspended" &&
      !window.confirm("Suspend this template? Existing forks keep working but no new forks allowed.")
    ) {
      return;
    }
    moderate.mutate({ id: template.id, body: { status: status as any } });
  };

  return (
    <div className="flex items-center gap-3 rounded-xl border border-border bg-card p-3">
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-violet-100 dark:bg-violet-500/15">
        <Sparkles className="h-4 w-4 text-violet-600 dark:text-violet-400" />
      </div>

      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-1.5">
          <Link
            href={`/hub/${template.slug}`}
            className="text-sm font-semibold hover:underline"
            target="_blank"
          >
            {template.title}
          </Link>
          <StatusBadge status={template.status} />
          {template.is_featured && (
            <Badge className="border-0 bg-amber-500 text-white text-[10px] gap-1">
              <Star className="h-2.5 w-2.5" />
              Featured
            </Badge>
          )}
        </div>
        <p className="mt-0.5 text-[11px] text-muted-foreground">
          by <span className="font-medium">{template.author_name}</span>
          {template.author_email && (
            <span className="text-muted-foreground/60"> · {template.author_email}</span>
          )}
          {" · "}
          {template.fork_count} forks
          {template.rating_count > 0 && (
            <> · ★ {Number(template.rating_avg ?? 0).toFixed(1)} ({template.rating_count})</>
          )}
        </p>
      </div>

      <div className="flex items-center gap-1 shrink-0">
        <Button
          variant={template.is_featured ? "default" : "outline"}
          size="sm"
          onClick={toggleFeatured}
          disabled={moderate.isPending}
        >
          {template.is_featured ? "Unfeature" : "Feature"}
        </Button>
        {template.status === "published" && (
          <Button
            variant="outline"
            size="sm"
            onClick={() => setStatus("suspended")}
            disabled={moderate.isPending}
          >
            Suspend
          </Button>
        )}
        {template.status === "suspended" && (
          <Button
            variant="outline"
            size="sm"
            onClick={() => setStatus("published")}
            disabled={moderate.isPending}
          >
            Republish
          </Button>
        )}
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    published: "border-emerald-500/40 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300",
    draft: "border-border bg-muted text-muted-foreground",
    suspended: "border-red-500/40 bg-red-500/10 text-red-700 dark:text-red-300",
    archived: "border-amber-500/40 bg-amber-500/10 text-amber-700 dark:text-amber-300",
  };
  return (
    <Badge variant="outline" className={`text-[10px] ${styles[status] ?? ""}`}>
      {status}
    </Badge>
  );
}

function Loader() {
  return (
    <div className="flex h-32 items-center justify-center">
      <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
    </div>
  );
}
function Empty() {
  return (
    <div className="rounded-xl border border-dashed border-border bg-card py-12 text-center text-xs text-muted-foreground">
      No templates match your filter.
    </div>
  );
}
