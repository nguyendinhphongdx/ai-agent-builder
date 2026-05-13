"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { NumberField, SelectField, TextField } from "@/components/form";
import { buildEmailPayload, triggersService } from "@/lib/api/triggersService";
import { TriggerFormShell } from "../components/TriggerFormShell";
import type { TriggerFormProps } from "./types";

export function EmailForm({
  workflows,
  forcedWorkflowId,
  onCancel,
  onDone,
}: TriggerFormProps) {
  const [form, setForm] = useState({
    workflow_id: forcedWorkflowId ?? "",
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
    mutationFn: () =>
      triggersService.create(
        buildEmailPayload({
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
        label="IMAP host"
        value={form.imap_host}
        onChange={(v) => setForm({ ...form, imap_host: v })}
        required
      />
      <NumberField
        label="Port"
        value={form.imap_port}
        onChange={(v) => setForm({ ...form, imap_port: v })}
      />
      <TextField
        label="Username"
        value={form.imap_username}
        onChange={(v) => setForm({ ...form, imap_username: v })}
        required
      />
      <TextField
        label="Password"
        type="password"
        value={form.imap_password}
        onChange={(v) => setForm({ ...form, imap_password: v })}
        required
      />
      <TextField
        label="Folder"
        value={form.imap_folder}
        onChange={(v) => setForm({ ...form, imap_folder: v })}
      />
      <NumberField
        label="Poll every (sec)"
        value={form.poll_interval_seconds}
        onChange={(v) => setForm({ ...form, poll_interval_seconds: v })}
        min={60}
        max={3600}
      />
    </TriggerFormShell>
  );
}
