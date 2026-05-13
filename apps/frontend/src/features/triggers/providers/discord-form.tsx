"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { SelectField, TextField } from "@/components/form";
import {
  buildDiscordPayload,
  triggersService,
} from "@/lib/api/triggersService";
import { TriggerFormShell } from "../components/TriggerFormShell";
import type { TriggerFormProps } from "./types";

export function DiscordForm({
  workflows,
  forcedWorkflowId,
  onCancel,
  onDone,
}: TriggerFormProps) {
  const [form, setForm] = useState({
    workflow_id: forcedWorkflowId ?? "",
    name: "",
    discord_application_id: "",
    discord_public_key: "",
    filter_command: "",
  });
  const createM = useMutation({
    mutationFn: () =>
      triggersService.create(
        buildDiscordPayload({
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
        label="Application ID"
        value={form.discord_application_id}
        onChange={(v) => setForm({ ...form, discord_application_id: v })}
        required
      />
      <TextField
        label="Public key (hex)"
        value={form.discord_public_key}
        onChange={(v) => setForm({ ...form, discord_public_key: v })}
        required
      />
      <TextField
        label="Command name (no slash)"
        value={form.filter_command}
        onChange={(v) => setForm({ ...form, filter_command: v })}
      />
    </TriggerFormShell>
  );
}
