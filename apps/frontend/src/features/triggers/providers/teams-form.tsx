"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { SelectField, TextField } from "@/components/form";
import { buildTeamsPayload, triggersService } from "@/lib/api/triggersService";
import { TriggerFormShell } from "../components/TriggerFormShell";
import type { TriggerFormProps } from "./types";

export function TeamsForm({
  workflows,
  forcedWorkflowId,
  onCancel,
  onDone,
}: TriggerFormProps) {
  const [form, setForm] = useState({
    workflow_id: forcedWorkflowId ?? "",
    name: "",
    hmac_secret_b64: "",
    filter_keyword: "",
  });
  const createM = useMutation({
    mutationFn: () =>
      triggersService.create(
        buildTeamsPayload({
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
        label="HMAC secret (base64)"
        type="password"
        value={form.hmac_secret_b64}
        onChange={(v) => setForm({ ...form, hmac_secret_b64: v })}
        required
      />
      <TextField
        label="Keyword filter (optional)"
        value={form.filter_keyword}
        onChange={(v) => setForm({ ...form, filter_keyword: v })}
      />
    </TriggerFormShell>
  );
}
