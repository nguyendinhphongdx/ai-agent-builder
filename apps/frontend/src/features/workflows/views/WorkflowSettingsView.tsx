"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, Loader2, Trash2, Zap, SlidersHorizontal } from "lucide-react";
import {
  SettingsCard,
  SettingsField,
  SettingsPageHeader,
  SettingsStack,
} from "@/features/settings/components/SettingsPrimitives";
import { TriggersView } from "@/features/triggers/views/TriggersView";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  useDeleteWorkflow,
  useRotateWebhookToken,
  useSaveWorkflow,
  useWorkflow,
} from "../hooks/useWorkflows";

interface WorkflowSettingsViewProps {
  workflowId: string;
}

type TabKey = "general" | "triggers";

const TABS: Array<{ key: TabKey; label: string; icon: React.ElementType }> = [
  { key: "general", label: "General", icon: SlidersHorizontal },
  { key: "triggers", label: "Triggers", icon: Zap },
];

/**
 * Per-workflow settings page — sits at /workflows/{id}/settings. Hosts
 * everything that's *about* a specific workflow rather than the
 * workspace as a whole: name/description, the webhook token, scoped
 * trigger management, and the danger-zone delete.
 *
 * Triggers tab embeds {@link TriggersView} with the workflow id pre-set
 * so the create forms skip the workflow picker and the lists are
 * filtered down to this workflow.
 */
export function WorkflowSettingsView({ workflowId }: WorkflowSettingsViewProps) {
  const router = useRouter();
  const [tab, setTab] = useState<TabKey>("general");
  const { data: workflow, isLoading } = useWorkflow(workflowId);

  if (isLoading || !workflow) {
    return (
      <div className="flex h-full items-center justify-center">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl p-6">
      <div className="mb-4">
        <Button
          variant="ghost"
          size="sm"
          className="gap-1.5 text-muted-foreground"
          onClick={() => router.push(`/workflows/${workflowId}`)}
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to editor
        </Button>
      </div>

      <SettingsPageHeader
        title={`Settings · ${workflow.name}`}
        description="Configure this workflow — general info, webhook, and the inbound triggers that can fire it."
      />

      <div className="mb-4 inline-flex rounded-md border border-border bg-muted/30 p-0.5">
        {TABS.map((t) => {
          const Icon = t.icon;
          return (
            <button
              key={t.key}
              type="button"
              onClick={() => setTab(t.key)}
              className={cn(
                "inline-flex items-center gap-1.5 rounded px-3 py-1 text-[12px] font-medium transition-colors",
                tab === t.key
                  ? "bg-background shadow-sm text-foreground"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              <Icon className="h-3 w-3" />
              {t.label}
            </button>
          );
        })}
      </div>

      {tab === "general" && <GeneralTab workflowId={workflowId} />}
      {tab === "triggers" && <TriggersView workflowId={workflowId} embedded />}
    </div>
  );
}

/* ─── General tab ──────────────────────────────────────────── */

function GeneralTab({ workflowId }: { workflowId: string }) {
  const { data: workflow } = useWorkflow(workflowId);
  const saveM = useSaveWorkflow(workflowId);
  const deleteM = useDeleteWorkflow();
  const rotateM = useRotateWebhookToken(workflowId);

  const [name, setName] = useState(workflow?.name ?? "");
  const [description, setDescription] = useState(workflow?.description ?? "");

  if (!workflow) return null;

  const dirty = name !== workflow.name || (description ?? "") !== (workflow.description ?? "");

  return (
    <SettingsStack>
      <SettingsCard
        title="Workflow info"
        description="Display name + description shown in the workflow list."
      >
        <div className="space-y-4">
          <SettingsField label="Name" htmlFor="wf-name">
            <input
              id="wf-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full rounded-md border border-border bg-background px-2 py-1.5 text-xs"
            />
          </SettingsField>
          <SettingsField label="Description" htmlFor="wf-desc">
            <textarea
              id="wf-desc"
              value={description ?? ""}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              className="w-full rounded-md border border-border bg-background px-2 py-1.5 text-xs"
            />
          </SettingsField>
          <div className="flex justify-end">
            <button
              type="button"
              disabled={!dirty || saveM.isPending}
              onClick={() => saveM.mutate({ name, description: description ?? "" })}
              className="inline-flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            >
              {saveM.isPending && <Loader2 className="h-3 w-3 animate-spin" />}
              Save
            </button>
          </div>
        </div>
      </SettingsCard>

      <SettingsCard
        title="Webhook"
        description="External HTTP endpoint that fires this workflow. Rotate the token if you suspect it leaked — the previous URL stops working immediately."
      >
        <div className="space-y-3">
          <SettingsField label="Token" hint="Append this token to the webhook URL.">
            <div className="flex items-center gap-2">
              <input
                readOnly
                value={workflow.webhook_token}
                className="w-full rounded-md border border-border bg-muted/30 px-2 py-1.5 font-mono text-[11px]"
              />
              <button
                type="button"
                onClick={() => navigator.clipboard.writeText(workflow.webhook_token)}
                className="rounded-md border border-border px-3 py-1.5 text-xs hover:bg-accent"
              >
                Copy
              </button>
            </div>
          </SettingsField>
          <div className="flex justify-end">
            <button
              type="button"
              disabled={rotateM.isPending}
              onClick={() => {
                if (window.confirm("Rotate webhook token? The current URL stops working immediately.")) {
                  rotateM.mutate();
                }
              }}
              className="inline-flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-xs hover:bg-accent disabled:opacity-50"
            >
              {rotateM.isPending && <Loader2 className="h-3 w-3 animate-spin" />}
              Rotate token
            </button>
          </div>
        </div>
      </SettingsCard>

      <SettingsCard
        title="Danger zone"
        description="Deleting a workflow removes its nodes, edges, and run history. Triggers attached to it are removed too."
        className="border-rose-500/40"
      >
        <div className="flex justify-end">
          <button
            type="button"
            disabled={deleteM.isPending}
            onClick={() => {
              if (window.confirm(`Delete "${workflow.name}"? This cannot be undone.`)) {
                deleteM.mutate(workflowId);
              }
            }}
            className="inline-flex items-center gap-1.5 rounded-md bg-rose-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-rose-600/90 disabled:opacity-50"
          >
            {deleteM.isPending ? (
              <Loader2 className="h-3 w-3 animate-spin" />
            ) : (
              <Trash2 className="h-3 w-3" />
            )}
            Delete workflow
          </button>
        </div>
      </SettingsCard>
    </SettingsStack>
  );
}
