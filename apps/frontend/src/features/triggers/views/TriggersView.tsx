"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AtSign, Hash, Loader2, MessageCircle, Plus, Trash2 } from "lucide-react";
import {
  SettingsCard,
  SettingsPageHeader,
  SettingsStack,
} from "@/features/settings/components/SettingsPrimitives";
import { cn } from "@/lib/utils";
import { workflowService } from "@/features/workflows/services/workflowService";
import {
  buildDiscordPayload,
  buildEmailPayload,
  buildSlackPayload,
  buildTeamsPayload,
  triggersService,
  type Trigger,
  type TriggerType,
} from "@/lib/api/triggersService";

type TabKey = Exclude<TriggerType, "scheduled">;

const TABS: Array<{ key: TabKey; label: string; icon: React.ElementType }> = [
  { key: "email", label: "Email (IMAP)", icon: AtSign },
  { key: "slack", label: "Slack", icon: MessageCircle },
  { key: "teams", label: "Microsoft Teams", icon: MessageCircle },
  { key: "discord", label: "Discord", icon: Hash },
];

/**
 * Cross-workflow trigger management page. Tabs by trigger type;
 * each tab lists triggers of that type in the active workspace and
 * a "+ New" button opens a create form. Per-row delete with confirm.
 *
 * All four tabs talk to the same unified ``/api/triggers`` router —
 * filtering by ``?type=`` for list, posting ``{type, config, ...}``
 * for create. The per-tab form builders package the user inputs
 * into the right ``config`` / ``credentials`` JSON shape.
 *
 * Scheduled triggers live on cron_trigger workflow nodes — managed
 * inline in the workflow editor, not here.
 */
export function TriggersView() {
  const [tab, setTab] = useState<TabKey>("email");

  return (
    <div className="mx-auto max-w-5xl p-6">
      <SettingsPageHeader
        title="Triggers"
        description="Inbound channels that fire workflow runs — email mailboxes, Slack events, Teams outgoing webhooks, Discord slash commands."
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

      <SettingsStack>
        {tab === "email" && <EmailTab />}
        {tab === "slack" && <SlackTab />}
        {tab === "teams" && <TeamsTab />}
        {tab === "discord" && <DiscordTab />}
      </SettingsStack>
    </div>
  );
}

/* ─── Shared bits ──────────────────────────────────────────── */

function useWorkflowList() {
  return useQuery({
    queryKey: ["workflows-for-triggers"],
    queryFn: () => workflowService.list(),
    staleTime: 60_000,
  });
}

function useTriggerList(type: TabKey) {
  return useQuery({
    queryKey: ["triggers", type],
    queryFn: () => triggersService.list({ type }),
  });
}

function useDeleteTrigger(type: TabKey) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => triggersService.remove(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["triggers", type] }),
  });
}

function ActiveBadge({ active }: { active: boolean }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider",
        active
          ? "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300"
          : "bg-muted/60 text-muted-foreground",
      )}
    >
      {active ? "active" : "off"}
    </span>
  );
}

function PrimaryButton({
  loading,
  children,
  ...rest
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { loading?: boolean }) {
  return (
    <button
      type="button"
      {...rest}
      className="inline-flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-50"
    >
      {loading ? <Loader2 className="h-3 w-3 animate-spin" /> : <Plus className="h-3 w-3" />}
      {children}
    </button>
  );
}

function DeleteButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="rounded-md p-1 text-muted-foreground hover:bg-rose-500/10 hover:text-rose-600"
      aria-label="Delete trigger"
    >
      <Trash2 className="h-3.5 w-3.5" />
    </button>
  );
}

function ErrorBanner({ message }: { message: string }) {
  return (
    <p className="rounded-md border border-rose-500/40 bg-rose-500/10 px-3 py-2 text-xs text-rose-700 dark:text-rose-300">
      {message}
    </p>
  );
}

/* ─── Email tab ────────────────────────────────────────────── */

function EmailTab() {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const wfQ = useWorkflowList();
  const listQ = useTriggerList("email");
  const removeM = useDeleteTrigger("email");

  return (
    <SettingsCard
      title="Email triggers"
      description="One IMAP mailbox per trigger. New messages enqueue a workflow run."
      action={!showForm ? <PrimaryButton onClick={() => setShowForm(true)}>New</PrimaryButton> : null}
    >
      {showForm && (
        <EmailTriggerForm
          workflows={wfQ.data ?? []}
          onCancel={() => setShowForm(false)}
          onDone={() => {
            setShowForm(false);
            qc.invalidateQueries({ queryKey: ["triggers", "email"] });
          }}
        />
      )}
      {listQ.isLoading ? (
        <Loader2 className="m-5 h-4 w-4 animate-spin text-muted-foreground" />
      ) : (listQ.data ?? []).length === 0 ? (
        <p className="px-5 py-6 text-xs text-muted-foreground">No email triggers yet.</p>
      ) : (
        <ul className="divide-y divide-border">
          {(listQ.data ?? []).map((t) => (
            <EmailRow key={t.id} trigger={t} onDelete={() => removeM.mutate(t.id)} />
          ))}
        </ul>
      )}
    </SettingsCard>
  );
}

function EmailRow({ trigger, onDelete }: { trigger: Trigger; onDelete: () => void }) {
  const cfg = trigger.config as {
    imap_host?: string;
    imap_port?: number;
    imap_username?: string;
    imap_folder?: string;
    poll_interval_seconds?: number;
  };
  return (
    <li className="flex items-center justify-between px-5 py-3">
      <div>
        <div className="flex items-center gap-2 text-sm font-medium">
          {trigger.name}
          <ActiveBadge active={trigger.is_active} />
        </div>
        <div className="mt-0.5 text-[11px] text-muted-foreground font-mono">
          {cfg.imap_username}@{cfg.imap_host}:{cfg.imap_port} · {cfg.imap_folder} ·
          poll every {cfg.poll_interval_seconds}s
        </div>
        {trigger.last_error && (
          <div className="mt-0.5 text-[11px] text-rose-600">⚠ {trigger.last_error}</div>
        )}
      </div>
      <DeleteButton
        onClick={() => {
          if (window.confirm("Delete this trigger?")) onDelete();
        }}
      />
    </li>
  );
}

function EmailTriggerForm({
  workflows,
  onCancel,
  onDone,
}: {
  workflows: Array<{ id: string; name: string }>;
  onCancel: () => void;
  onDone: () => void;
}) {
  const [form, setForm] = useState({
    workflow_id: "",
    name: "",
    imap_host: "",
    imap_port: 993,
    imap_use_ssl: true,
    imap_username: "",
    imap_password: "",
    imap_folder: "INBOX",
    poll_interval_seconds: 300,
    mark_seen: true,
  });
  const createM = useMutation({
    mutationFn: () => triggersService.create(buildEmailPayload(form)),
    onSuccess: onDone,
  });

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        createM.mutate();
      }}
      className="space-y-3 border-b border-border p-5"
    >
      <div className="grid grid-cols-2 gap-3">
        <SelectInput
          label="Workflow"
          value={form.workflow_id}
          onChange={(v) => setForm({ ...form, workflow_id: v })}
          options={workflows.map((w) => ({ label: w.name, value: w.id }))}
          required
        />
        <TextInput label="Name" value={form.name} onChange={(v) => setForm({ ...form, name: v })} required />
        <TextInput label="IMAP host" value={form.imap_host} onChange={(v) => setForm({ ...form, imap_host: v })} required />
        <NumberInput label="Port" value={form.imap_port} onChange={(v) => setForm({ ...form, imap_port: v })} />
        <TextInput label="Username" value={form.imap_username} onChange={(v) => setForm({ ...form, imap_username: v })} required />
        <TextInput label="Password" type="password" value={form.imap_password} onChange={(v) => setForm({ ...form, imap_password: v })} required />
        <TextInput label="Folder" value={form.imap_folder} onChange={(v) => setForm({ ...form, imap_folder: v })} />
        <NumberInput
          label="Poll every (sec)"
          value={form.poll_interval_seconds}
          onChange={(v) => setForm({ ...form, poll_interval_seconds: v })}
          min={60}
          max={3600}
        />
      </div>
      {createM.error && <ErrorBanner message={extractError(createM.error)} />}
      <FormActions onCancel={onCancel} loading={createM.isPending} />
    </form>
  );
}

/* ─── Slack tab ────────────────────────────────────────────── */

function SlackTab() {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const wfQ = useWorkflowList();
  const listQ = useTriggerList("slack");
  const removeM = useDeleteTrigger("slack");

  return (
    <SettingsCard
      title="Slack triggers"
      description="App mentions, channel messages, slash commands. Point your Slack app's Event URL at /api/triggers/slack/events."
      action={!showForm ? <PrimaryButton onClick={() => setShowForm(true)}>New</PrimaryButton> : null}
    >
      {showForm && (
        <SlackTriggerForm
          workflows={wfQ.data ?? []}
          onCancel={() => setShowForm(false)}
          onDone={() => {
            setShowForm(false);
            qc.invalidateQueries({ queryKey: ["triggers", "slack"] });
          }}
        />
      )}
      {listQ.isLoading ? (
        <Loader2 className="m-5 h-4 w-4 animate-spin text-muted-foreground" />
      ) : (listQ.data ?? []).length === 0 ? (
        <p className="px-5 py-6 text-xs text-muted-foreground">No Slack triggers yet.</p>
      ) : (
        <ul className="divide-y divide-border">
          {(listQ.data ?? []).map((t) => (
            <SlackRow key={t.id} trigger={t} onDelete={() => removeM.mutate(t.id)} />
          ))}
        </ul>
      )}
    </SettingsCard>
  );
}

function SlackRow({ trigger, onDelete }: { trigger: Trigger; onDelete: () => void }) {
  const cfg = trigger.config as {
    slack_team_id?: string;
    filter_event_type?: string;
    filter_channel_id?: string;
    filter_command?: string;
    filter_keyword?: string;
  };
  return (
    <li className="flex items-center justify-between px-5 py-3">
      <div>
        <div className="flex items-center gap-2 text-sm font-medium">
          {trigger.name}
          <ActiveBadge active={trigger.is_active} />
        </div>
        <div className="mt-0.5 text-[11px] font-mono text-muted-foreground">
          {cfg.slack_team_id} · {cfg.filter_event_type}
          {cfg.filter_channel_id && ` · #${cfg.filter_channel_id}`}
          {cfg.filter_command && ` · ${cfg.filter_command}`}
          {cfg.filter_keyword && ` · contains "${cfg.filter_keyword}"`}
        </div>
      </div>
      <DeleteButton
        onClick={() => {
          if (window.confirm("Delete this trigger?")) onDelete();
        }}
      />
    </li>
  );
}

function SlackTriggerForm({
  workflows,
  onCancel,
  onDone,
}: {
  workflows: Array<{ id: string; name: string }>;
  onCancel: () => void;
  onDone: () => void;
}) {
  const [form, setForm] = useState({
    workflow_id: "",
    name: "",
    slack_team_id: "",
    filter_event_type: "app_mention" as "app_mention" | "message" | "slash_command",
    filter_channel_id: "",
    filter_command: "",
    filter_keyword: "",
  });
  const createM = useMutation({
    mutationFn: () => triggersService.create(buildSlackPayload(form)),
    onSuccess: onDone,
  });

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        createM.mutate();
      }}
      className="space-y-3 border-b border-border p-5"
    >
      <div className="grid grid-cols-2 gap-3">
        <SelectInput
          label="Workflow"
          value={form.workflow_id}
          onChange={(v) => setForm({ ...form, workflow_id: v })}
          options={workflows.map((w) => ({ label: w.name, value: w.id }))}
          required
        />
        <TextInput label="Name" value={form.name} onChange={(v) => setForm({ ...form, name: v })} required />
        <TextInput label="Slack team id" value={form.slack_team_id} onChange={(v) => setForm({ ...form, slack_team_id: v })} required />
        <SelectInput
          label="Event type"
          value={form.filter_event_type}
          onChange={(v) =>
            setForm({ ...form, filter_event_type: v as typeof form.filter_event_type })
          }
          options={[
            { label: "App mention (@bot)", value: "app_mention" },
            { label: "Channel message", value: "message" },
            { label: "Slash command", value: "slash_command" },
          ]}
        />
        <TextInput label="Channel id (optional)" value={form.filter_channel_id} onChange={(v) => setForm({ ...form, filter_channel_id: v })} />
        <TextInput label="Slash command (e.g. /agent)" value={form.filter_command} onChange={(v) => setForm({ ...form, filter_command: v })} />
        <TextInput label="Keyword filter (optional)" value={form.filter_keyword} onChange={(v) => setForm({ ...form, filter_keyword: v })} />
      </div>
      {createM.error && <ErrorBanner message={extractError(createM.error)} />}
      <FormActions onCancel={onCancel} loading={createM.isPending} />
    </form>
  );
}

/* ─── Teams tab ────────────────────────────────────────────── */

function TeamsTab() {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const wfQ = useWorkflowList();
  const listQ = useTriggerList("teams");
  const removeM = useDeleteTrigger("teams");

  return (
    <SettingsCard
      title="Microsoft Teams triggers"
      description="Outgoing webhooks. Each trigger gets a unique URL — paste the HMAC secret Teams shows when you add the webhook."
      action={!showForm ? <PrimaryButton onClick={() => setShowForm(true)}>New</PrimaryButton> : null}
    >
      {showForm && (
        <TeamsTriggerForm
          workflows={wfQ.data ?? []}
          onCancel={() => setShowForm(false)}
          onDone={() => {
            setShowForm(false);
            qc.invalidateQueries({ queryKey: ["triggers", "teams"] });
          }}
        />
      )}
      {listQ.isLoading ? (
        <Loader2 className="m-5 h-4 w-4 animate-spin text-muted-foreground" />
      ) : (listQ.data ?? []).length === 0 ? (
        <p className="px-5 py-6 text-xs text-muted-foreground">No Teams triggers yet.</p>
      ) : (
        <ul className="divide-y divide-border">
          {(listQ.data ?? []).map((t) => (
            <TeamsRow key={t.id} trigger={t} onDelete={() => removeM.mutate(t.id)} />
          ))}
        </ul>
      )}
    </SettingsCard>
  );
}

function TeamsRow({ trigger, onDelete }: { trigger: Trigger; onDelete: () => void }) {
  const cfg = trigger.config as { filter_keyword?: string };
  return (
    <li className="flex items-center justify-between px-5 py-3">
      <div>
        <div className="flex items-center gap-2 text-sm font-medium">
          {trigger.name}
          <ActiveBadge active={trigger.is_active} />
        </div>
        <div className="mt-0.5 text-[11px] font-mono text-muted-foreground">
          Webhook URL: /api/triggers/teams/{trigger.id}/events
          {cfg.filter_keyword && ` · contains "${cfg.filter_keyword}"`}
        </div>
      </div>
      <DeleteButton
        onClick={() => {
          if (window.confirm("Delete this trigger?")) onDelete();
        }}
      />
    </li>
  );
}

function TeamsTriggerForm({
  workflows,
  onCancel,
  onDone,
}: {
  workflows: Array<{ id: string; name: string }>;
  onCancel: () => void;
  onDone: () => void;
}) {
  const [form, setForm] = useState({
    workflow_id: "",
    name: "",
    hmac_secret_b64: "",
    filter_keyword: "",
  });
  const createM = useMutation({
    mutationFn: () => triggersService.create(buildTeamsPayload(form)),
    onSuccess: onDone,
  });

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        createM.mutate();
      }}
      className="space-y-3 border-b border-border p-5"
    >
      <div className="grid grid-cols-2 gap-3">
        <SelectInput
          label="Workflow"
          value={form.workflow_id}
          onChange={(v) => setForm({ ...form, workflow_id: v })}
          options={workflows.map((w) => ({ label: w.name, value: w.id }))}
          required
        />
        <TextInput label="Name" value={form.name} onChange={(v) => setForm({ ...form, name: v })} required />
        <TextInput
          label="HMAC secret (base64)"
          type="password"
          value={form.hmac_secret_b64}
          onChange={(v) => setForm({ ...form, hmac_secret_b64: v })}
          required
        />
        <TextInput label="Keyword filter (optional)" value={form.filter_keyword} onChange={(v) => setForm({ ...form, filter_keyword: v })} />
      </div>
      {createM.error && <ErrorBanner message={extractError(createM.error)} />}
      <FormActions onCancel={onCancel} loading={createM.isPending} />
    </form>
  );
}

/* ─── Discord tab ──────────────────────────────────────────── */

function DiscordTab() {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const wfQ = useWorkflowList();
  const listQ = useTriggerList("discord");
  const removeM = useDeleteTrigger("discord");

  return (
    <SettingsCard
      title="Discord triggers"
      description="Slash-command interactions. Point your bot's Interactions Endpoint URL at /api/triggers/discord/interactions."
      action={!showForm ? <PrimaryButton onClick={() => setShowForm(true)}>New</PrimaryButton> : null}
    >
      {showForm && (
        <DiscordTriggerForm
          workflows={wfQ.data ?? []}
          onCancel={() => setShowForm(false)}
          onDone={() => {
            setShowForm(false);
            qc.invalidateQueries({ queryKey: ["triggers", "discord"] });
          }}
        />
      )}
      {listQ.isLoading ? (
        <Loader2 className="m-5 h-4 w-4 animate-spin text-muted-foreground" />
      ) : (listQ.data ?? []).length === 0 ? (
        <p className="px-5 py-6 text-xs text-muted-foreground">No Discord triggers yet.</p>
      ) : (
        <ul className="divide-y divide-border">
          {(listQ.data ?? []).map((t) => (
            <DiscordRow key={t.id} trigger={t} onDelete={() => removeM.mutate(t.id)} />
          ))}
        </ul>
      )}
    </SettingsCard>
  );
}

function DiscordRow({ trigger, onDelete }: { trigger: Trigger; onDelete: () => void }) {
  const cfg = trigger.config as {
    discord_application_id?: string;
    filter_command?: string;
  };
  return (
    <li className="flex items-center justify-between px-5 py-3">
      <div>
        <div className="flex items-center gap-2 text-sm font-medium">
          {trigger.name}
          <ActiveBadge active={trigger.is_active} />
        </div>
        <div className="mt-0.5 text-[11px] font-mono text-muted-foreground">
          App {cfg.discord_application_id}
          {cfg.filter_command && ` · /${cfg.filter_command}`}
        </div>
      </div>
      <DeleteButton
        onClick={() => {
          if (window.confirm("Delete this trigger?")) onDelete();
        }}
      />
    </li>
  );
}

function DiscordTriggerForm({
  workflows,
  onCancel,
  onDone,
}: {
  workflows: Array<{ id: string; name: string }>;
  onCancel: () => void;
  onDone: () => void;
}) {
  const [form, setForm] = useState({
    workflow_id: "",
    name: "",
    discord_application_id: "",
    discord_public_key: "",
    filter_command: "",
  });
  const createM = useMutation({
    mutationFn: () => triggersService.create(buildDiscordPayload(form)),
    onSuccess: onDone,
  });

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        createM.mutate();
      }}
      className="space-y-3 border-b border-border p-5"
    >
      <div className="grid grid-cols-2 gap-3">
        <SelectInput
          label="Workflow"
          value={form.workflow_id}
          onChange={(v) => setForm({ ...form, workflow_id: v })}
          options={workflows.map((w) => ({ label: w.name, value: w.id }))}
          required
        />
        <TextInput label="Name" value={form.name} onChange={(v) => setForm({ ...form, name: v })} required />
        <TextInput
          label="Application ID"
          value={form.discord_application_id}
          onChange={(v) => setForm({ ...form, discord_application_id: v })}
          required
        />
        <TextInput
          label="Public key (hex)"
          value={form.discord_public_key}
          onChange={(v) => setForm({ ...form, discord_public_key: v })}
          required
        />
        <TextInput label="Command name (no slash)" value={form.filter_command} onChange={(v) => setForm({ ...form, filter_command: v })} />
      </div>
      {createM.error && <ErrorBanner message={extractError(createM.error)} />}
      <FormActions onCancel={onCancel} loading={createM.isPending} />
    </form>
  );
}

/* ─── Field primitives ─────────────────────────────────────── */

function TextInput({
  label,
  value,
  onChange,
  type = "text",
  required,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  type?: string;
  required?: boolean;
}) {
  return (
    <label className="block">
      <span className="mb-1 block text-[11px] font-medium text-muted-foreground">{label}</span>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        required={required}
        className="w-full rounded-md border border-border bg-background px-2 py-1.5 text-xs"
      />
    </label>
  );
}

function NumberInput({
  label,
  value,
  onChange,
  min,
  max,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  min?: number;
  max?: number;
}) {
  return (
    <label className="block">
      <span className="mb-1 block text-[11px] font-medium text-muted-foreground">{label}</span>
      <input
        type="number"
        value={value}
        min={min}
        max={max}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full rounded-md border border-border bg-background px-2 py-1.5 text-xs"
      />
    </label>
  );
}

function SelectInput({
  label,
  value,
  onChange,
  options,
  required,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: Array<{ label: string; value: string }>;
  required?: boolean;
}) {
  return (
    <label className="block">
      <span className="mb-1 block text-[11px] font-medium text-muted-foreground">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        required={required}
        className="w-full rounded-md border border-border bg-background px-2 py-1.5 text-xs"
      >
        <option value="" disabled>
          Select…
        </option>
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </label>
  );
}

function FormActions({ onCancel, loading }: { onCancel: () => void; loading: boolean }) {
  return (
    <div className="flex justify-end gap-2 pt-2">
      <button
        type="button"
        onClick={onCancel}
        className="rounded-md border border-border px-3 py-1.5 text-xs hover:bg-accent"
      >
        Cancel
      </button>
      <button
        type="submit"
        disabled={loading}
        className="inline-flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
      >
        {loading && <Loader2 className="h-3 w-3 animate-spin" />}
        Save
      </button>
    </div>
  );
}

/* ─── Error extraction ─────────────────────────────────────── */

function extractError(err: unknown): string {
  const anyErr = err as {
    response?: { data?: { detail?: string | object } };
    message?: string;
  };
  const detail = anyErr?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (detail && typeof detail === "object") return JSON.stringify(detail);
  return anyErr?.message ?? "Request failed";
}
