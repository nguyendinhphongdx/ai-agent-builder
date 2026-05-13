"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { SelectField, TextField } from "@/components/form";
import { buildSlackPayload, triggersService } from "@/lib/api/triggersService";
import { TriggerFormShell } from "../components/TriggerFormShell";
import type { TriggerFormProps } from "./types";

type SlackEventType = "app_mention" | "message" | "slash_command";

export function SlackForm({
  workflows,
  forcedWorkflowId,
  onCancel,
  onDone,
}: TriggerFormProps) {
  const [form, setForm] = useState({
    workflow_id: forcedWorkflowId ?? "",
    name: "",
    slack_team_id: "",
    filter_event_type: "app_mention" as SlackEventType,
    filter_channel_id: "",
    filter_command: "",
    filter_keyword: "",
  });
  const createM = useMutation({
    mutationFn: () =>
      triggersService.create(
        buildSlackPayload({
          ...form,
          workflow_id: forcedWorkflowId ?? form.workflow_id,
        }),
      ),
    onSuccess: onDone,
  });

  return (
    <TriggerFormShell
      onSubmit={() => createM.mutate()}
      onCancel={onCancel}
      isPending={createM.isPending}
      error={createM.error}
    >
      {!forcedWorkflowId && (
        <SelectField
          label="Workflow"
          value={form.workflow_id}
          onChange={(v) => setForm({ ...form, workflow_id: v })}
          options={workflows.map((w) => ({ label: w.name, value: w.id }))}
          required
        />
      )}
      <TextField
        label="Name"
        value={form.name}
        onChange={(v) => setForm({ ...form, name: v })}
        required
      />
      <TextField
        label="Slack team id"
        value={form.slack_team_id}
        onChange={(v) => setForm({ ...form, slack_team_id: v })}
        required
      />
      <SelectField
        label="Event type"
        value={form.filter_event_type}
        onChange={(v) =>
          setForm({ ...form, filter_event_type: v as SlackEventType })
        }
        options={[
          { label: "App mention (@bot)", value: "app_mention" },
          { label: "Channel message", value: "message" },
          { label: "Slash command", value: "slash_command" },
        ]}
      />
      <TextField
        label="Channel id (optional)"
        value={form.filter_channel_id}
        onChange={(v) => setForm({ ...form, filter_channel_id: v })}
      />
      <TextField
        label="Slash command (e.g. /agent)"
        value={form.filter_command}
        onChange={(v) => setForm({ ...form, filter_command: v })}
      />
      <TextField
        label="Keyword filter (optional)"
        value={form.filter_keyword}
        onChange={(v) => setForm({ ...form, filter_keyword: v })}
      />
    </TriggerFormShell>
  );
}
