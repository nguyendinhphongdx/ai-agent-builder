"use client";

import { useCallback, useState } from "react";
import { Check, Copy } from "lucide-react";
import { useParams } from "next/navigation";
import { Input } from "@/components/ui/input";
import { TextField, TextareaField, SelectField } from "../../components/node-inspector/fields";
import { useNodeConfig } from "../../hooks/useNodeConfig";
import type { PanelProps } from "../types";

const RESPONSE_MODE_OPTIONS = [
  {
    label: "Immediately",
    value: "immediately",
  },
  {
    label: "When Last Node Finishes",
    value: "lastNode",
  },
];

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

function buildWebhookUrl(workflowId: string, path: string): string {
  const normalised = path ? (path.startsWith("/") ? path : `/${path}`) : "/";
  return `${API_BASE}/webhooks/${workflowId}${normalised}`;
}

export default function WebhookTriggerPanel({ id }: PanelProps) {
  const { config, updateConfig } = useNodeConfig(id);
  const params = useParams<{ id: string }>();
  const workflowId = params?.id ?? "";

  const path = (config.path as string) ?? "";
  const responseMode = (config.response_mode as string) ?? "immediately";
  const responseCode = (config.response_code as number) ?? 200;
  const responseData = (config.response_data as string) ?? "";

  const url = buildWebhookUrl(workflowId, path);

  const [copied, setCopied] = useState(false);
  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // ignore
    }
  }, [url]);

  return (
    <div className="space-y-4">
      {/* Webhook URL */}
      <div className="space-y-1.5">
        <label className="text-xs font-medium text-muted-foreground">Webhook URL</label>
        <div className="flex items-center gap-2">
          <Input
            value={url}
            readOnly
            className="font-mono text-xs"
            onFocus={(e) => e.currentTarget.select()}
          />
          <button
            type="button"
            onClick={handleCopy}
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md border border-border bg-background text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
            aria-label="Copy URL"
          >
            {copied ? (
              <Check className="h-3.5 w-3.5 text-emerald-500" />
            ) : (
              <Copy className="h-3.5 w-3.5" />
            )}
          </button>
        </div>
        <p className="text-[10px] text-muted-foreground">
          Workflow must be active before this URL responds.
        </p>
      </div>

      {/* HTTP Method — locked to POST for now */}
      <div className="space-y-1.5">
        <label className="text-xs font-medium text-muted-foreground">HTTP Method</label>
        <Input value="POST" readOnly disabled className="font-mono text-xs" />
      </div>

      <TextField
        label="Path"
        value={path}
        onChange={(v) => updateConfig("path", v)}
        placeholder="/webhook"
      />

      <SelectField
        label="Respond"
        value={responseMode}
        options={RESPONSE_MODE_OPTIONS}
        onChange={(v) => updateConfig("response_mode", v)}
      />

      <div className="space-y-1.5">
        <label className="text-xs font-medium text-muted-foreground">Response Code</label>
        <Input
          type="number"
          min={100}
          max={599}
          value={responseCode}
          onChange={(e) => updateConfig("response_code", Number(e.target.value))}
        />
      </div>

      {responseMode === "immediately" && (
        <TextareaField
          label="Response Data"
          value={responseData}
          onChange={(v) => updateConfig("response_data", v)}
          placeholder='"ok" or {"status": "received"}'
        />
      )}
    </div>
  );
}
