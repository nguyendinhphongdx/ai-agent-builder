"use client";

import { useState } from "react";
import Link from "next/link";
import {
  Archive,
  ExternalLink,
  GitCommit,
  Loader2,
  Pencil,
  Sparkles,
  Users,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { MoreHorizontal } from "lucide-react";
import { EditTemplateDialog } from "../components/EditTemplateDialog";
import { PublishVersionDialog } from "../components/PublishVersionDialog";
import { formatPrice } from "../lib/price";
import {
  useArchiveTemplate,
  useMyPublishedTemplates,
  useTemplateVersions,
} from "../hooks/useTemplates";
import type { TemplateSummary } from "../types";

export function HubMyTemplatesView() {
  const { data: templates, isLoading } = useMyPublishedTemplates();
  const [editing, setEditing] = useState<TemplateSummary | null>(null);
  const [publishing, setPublishing] = useState<TemplateSummary | null>(null);

  return (
    <div className="mx-auto max-w-5xl px-4 py-6">
      <header className="mb-6 flex items-end justify-between">
        <div>
          <h1 className="font-heading text-2xl font-semibold">My templates</h1>
          <p className="text-sm text-muted-foreground">
            Agents you've published to the Hub.
          </p>
        </div>
        <Link
          href="/hub"
          className="text-xs text-muted-foreground transition-colors hover:text-foreground"
        >
          ← Browse hub
        </Link>
      </header>

      {isLoading ? (
        <div className="flex h-40 items-center justify-center">
          <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
        </div>
      ) : !templates || templates.length === 0 ? (
        <EmptyState />
      ) : (
        <div className="space-y-2">
          {templates.map((t) => (
            <TemplateRow
              key={t.id}
              template={t}
              onEdit={() => setEditing(t)}
              onPublishVersion={() => setPublishing(t)}
            />
          ))}
        </div>
      )}

      {editing && (
        <EditTemplateDialog
          template={editing}
          open={!!editing}
          onOpenChange={(open) => !open && setEditing(null)}
        />
      )}

      {publishing && (
        <PublishVersionWrapper
          template={publishing}
          open={!!publishing}
          onOpenChange={(open) => !open && setPublishing(null)}
        />
      )}
    </div>
  );
}

/** Loads the current version separately so the dialog shows the right preview. */
function PublishVersionWrapper({
  template,
  open,
  onOpenChange,
}: {
  template: TemplateSummary;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const { data: versions } = useTemplateVersions(template.id);
  const current = versions?.find((v) => v.is_current)?.version ?? null;
  return (
    <PublishVersionDialog
      templateId={template.id}
      templateTitle={template.title}
      currentVersion={current}
      open={open}
      onOpenChange={onOpenChange}
    />
  );
}

function TemplateRow({
  template,
  onEdit,
  onPublishVersion,
}: {
  template: TemplateSummary;
  onEdit: () => void;
  onPublishVersion: () => void;
}) {
  const archive = useArchiveTemplate();
  const isFree = template.price_cents === 0;
  const status = (template as TemplateSummary & { status?: string }).status;

  return (
    <div className="flex items-center gap-4 rounded-xl border border-border bg-card p-4">
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-violet-100 dark:bg-violet-500/15">
        <Sparkles className="h-5 w-5 text-violet-600 dark:text-violet-400" />
      </div>

      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <Link
            href={`/hub/${template.slug}`}
            className="text-sm font-semibold hover:underline"
          >
            {template.title}
          </Link>
          {status === "archived" && (
            <Badge variant="secondary" className="text-[10px]">
              Archived
            </Badge>
          )}
          {template.is_featured && (
            <Badge className="border-0 bg-amber-500 text-white text-[10px]">
              Featured
            </Badge>
          )}
          <Badge
            variant="outline"
            className={isFree ? "text-[10px] text-emerald-600" : "text-[10px]"}
          >
            {formatPrice(template.price_cents, template.currency)}
          </Badge>
        </div>
        <p className="mt-0.5 line-clamp-1 text-xs text-muted-foreground">
          {template.description || "No description"}
        </p>
      </div>

      <div className="flex items-center gap-3 shrink-0 text-xs text-muted-foreground">
        <span className="flex items-center gap-1">
          <Users className="h-3 w-3" />
          {template.fork_count}
        </span>
      </div>

      <div className="flex items-center gap-1 shrink-0">
        <Button variant="outline" size="sm" className="gap-1.5" onClick={onPublishVersion}>
          <GitCommit className="h-3 w-3" />
          New version
        </Button>
        <Button variant="outline" size="sm" className="gap-1.5" onClick={onEdit}>
          <Pencil className="h-3 w-3" />
          Edit
        </Button>

        <Link
          href={`/hub/${template.slug}`}
          className="rounded-md border border-border bg-background p-1.5 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
          title="View public page"
        >
          <ExternalLink className="h-3.5 w-3.5" />
        </Link>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" size="icon-sm" className="h-7 w-7">
              <MoreHorizontal className="h-3.5 w-3.5" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-40">
            <DropdownMenuItem
              onClick={() => {
                if (
                  window.confirm(
                    "Archive this template? Existing forks keep working, but new users can't fork it anymore.",
                  )
                ) {
                  archive.mutate(template.id);
                }
              }}
              disabled={archive.isPending || status === "archived"}
            >
              <Archive className="mr-2 h-3.5 w-3.5" />
              Archive
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border bg-card py-16 text-center">
      <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-violet-100 dark:bg-violet-500/15">
        <Sparkles className="h-5 w-5 text-violet-500" />
      </div>
      <p className="text-sm font-medium text-foreground">No templates yet</p>
      <p className="mt-1 text-xs text-muted-foreground">
        Open one of your agents and click <span className="font-medium">Publish</span> to share it.
      </p>
      <Button variant="outline" size="sm" className="mt-4" asChild>
        <Link href={"/ws/agents"}>Go to agents</Link>
      </Button>
    </div>
  );
}
