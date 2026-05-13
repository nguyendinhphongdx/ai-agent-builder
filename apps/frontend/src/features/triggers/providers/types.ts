import type { ComponentType } from "react";
import type { LucideIcon } from "lucide-react";
import type { Trigger, TriggerType } from "@/lib/api/triggersService";

/**
 * Trigger types that have an inbound-channel UI in the Triggers page.
 * `scheduled` triggers live on workflow nodes (managed in the editor),
 * not here.
 */
export type ProviderTriggerType = Exclude<TriggerType, "scheduled">;

export type TriggerFormProps = {
  /** List of workflows the user can attach this trigger to. */
  workflows: Array<{ id: string; name: string }>;
  /** If set, hides the workflow picker and forces this id on submit
   *  (used when embedded inside a single-workflow settings page). */
  forcedWorkflowId?: string;
  /** Called when the user dismisses the form without saving. */
  onCancel: () => void;
  /** Called after a successful create; CRUDListView invalidates the list. */
  onDone: () => void;
};

export type TriggerRowProps = {
  item: Trigger;
  onDelete: () => void;
};

/**
 * Everything the Triggers page needs to know about an inbound channel,
 * in one declarative bundle. Adding a 5th provider is a new file in
 * `providers/<name>.ts` plus an entry in the `TRIGGER_PROVIDERS` array
 * — no changes to TriggersView itself.
 */
export interface TriggerProvider {
  /** Discriminator that matches `trigger.type` from the backend. */
  type: ProviderTriggerType;
  /** Short label for the tab strip. */
  label: string;
  /** Icon shown alongside the tab label. */
  icon: LucideIcon;
  /** Card-header copy when this tab is active. */
  cardTitle: string;
  cardDescription: string;
  /** Copy shown when the list is empty for this provider. */
  emptyMessage: string;
  /** Renders a single row in the list. */
  RowComponent: ComponentType<TriggerRowProps>;
  /** Renders the "+ New" form. */
  FormComponent: ComponentType<TriggerFormProps>;
}
