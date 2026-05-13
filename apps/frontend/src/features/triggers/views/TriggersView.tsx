"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { CRUDListView } from "@/components/data/CRUDListView";
import {
  SettingsPageHeader,
  SettingsStack,
} from "@/features/settings/components/SettingsPrimitives";
import { cn } from "@/lib/utils";
import { workflowService } from "@/features/workflows/services/workflowService";
import { triggersService, type Trigger } from "@/lib/api/triggersService";
import {
  TRIGGER_PROVIDERS,
  type TriggerProvider,
} from "../providers";

interface TriggersViewProps {
  /**
   * When set, scopes the list + create-form to a single workflow —
   * the workflow picker is hidden and create payloads use this id.
   * Used by the workflow-settings page (the workflow context is
   * implicit there). Omit for the cross-workflow Settings page.
   */
  workflowId?: string;
  /** Disable the outer page header + max-width wrapper when embedded
   *  inside another settings container (e.g. WorkflowSettingsView). */
  embedded?: boolean;
}

/**
 * Trigger management UI — one tab per inbound channel. Each provider
 * is a declarative bundle in `../providers/<name>.ts`; this view is the
 * shell that picks the active provider and delegates to <CRUDListView>.
 *
 * To add a new inbound channel:
 *   1. Add a new `providers/<name>.ts` (+ row + form files) following
 *      the `TriggerProvider` interface.
 *   2. Append it to `TRIGGER_PROVIDERS` in `providers/index.ts`.
 *
 * Scheduled triggers live on cron_trigger workflow nodes — managed
 * inline in the workflow editor, not here.
 */
export function TriggersView({
  workflowId,
  embedded = false,
}: TriggersViewProps = {}) {
  const [activeType, setActiveType] = useState(TRIGGER_PROVIDERS[0].type);
  const active =
    TRIGGER_PROVIDERS.find((p) => p.type === activeType) ?? TRIGGER_PROVIDERS[0];

  const wfQ = useQuery({
    queryKey: ["workflows-for-triggers"],
    queryFn: () => workflowService.list(),
    staleTime: 60_000,
  });

  const tabs = (
    <div className="mb-4 inline-flex rounded-md border border-border bg-muted/30 p-0.5">
      {TRIGGER_PROVIDERS.map((p) => {
        const Icon = p.icon;
        return (
          <button
            key={p.type}
            type="button"
            onClick={() => setActiveType(p.type)}
            className={cn(
              "inline-flex items-center gap-1.5 rounded px-3 py-1 text-[12px] font-medium transition-colors",
              activeType === p.type
                ? "bg-background text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            <Icon className="h-3 w-3" />
            {p.label}
          </button>
        );
      })}
    </div>
  );

  const body = (
    <SettingsStack>
      <ProviderPanel
        provider={active}
        workflowId={workflowId}
        workflows={wfQ.data ?? []}
      />
    </SettingsStack>
  );

  if (embedded) {
    return (
      <div className="space-y-4">
        {tabs}
        {body}
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl p-6">
      <SettingsPageHeader
        title="Triggers"
        description="Inbound channels that fire workflow runs — email mailboxes, Slack events, Teams outgoing webhooks, Discord slash commands."
      />
      {tabs}
      {body}
    </div>
  );
}

function ProviderPanel({
  provider,
  workflowId,
  workflows,
}: {
  provider: TriggerProvider;
  workflowId?: string;
  workflows: Array<{ id: string; name: string }>;
}) {
  const Form = provider.FormComponent;
  return (
    <CRUDListView<Trigger>
      title={provider.cardTitle}
      description={provider.cardDescription}
      emptyMessage={provider.emptyMessage}
      queryKey={["triggers", provider.type, workflowId ?? "all"]}
      fetcher={() =>
        triggersService.list({ type: provider.type, workflow_id: workflowId })
      }
      deleter={(id) => triggersService.remove(id)}
      RowComponent={provider.RowComponent}
      confirmDelete={() => "Delete this trigger?"}
      renderForm={({ onCancel, onDone }) => (
        <Form
          workflows={workflows}
          forcedWorkflowId={workflowId}
          onCancel={onCancel}
          onDone={onDone}
        />
      )}
    />
  );
}
