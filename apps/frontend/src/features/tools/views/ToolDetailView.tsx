"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, useCallback } from "react";
import {
  ArrowLeft, Play, Loader2, CheckCircle2, XCircle, Clock,
  Trash2, Power, Info, Shield, Globe, Code,
  Database, Wrench, Search, Terminal, FlaskConical,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { StatusBadge } from "@/components/ui/status-badge";
import { useTool, useUpdateTool, useTestTool, useDeleteTool } from "../hooks/useTools";
import { TOOL_TYPE_META, type JsonSchema, type ToolType } from "../types";
import { ToolConfigRenderer } from "../components/ToolConfigRenderer";
import { VariableSchemaEditor } from "../components/VariableSchemaEditor";
import { cn } from "@/lib/utils";

const ICON_MAP: Record<string, React.ElementType> = {
  globe: Globe, code: Code, database: Database, wrench: Wrench, spider: Search,
};

const TYPE_COLORS: Record<ToolType, { bg: string; border: string; text: string; iconBg: string; badge: string }> = {
  http_request: {
    bg: "bg-blue-50 dark:bg-blue-500/10", border: "border-blue-200 dark:border-blue-500/30",
    text: "text-blue-700 dark:text-blue-300", iconBg: "bg-blue-100 dark:bg-blue-500/20",
    badge: "bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-500/10 dark:text-blue-300 dark:border-blue-500/30",
  },
  code_exec: {
    bg: "bg-violet-50 dark:bg-violet-500/10", border: "border-violet-200 dark:border-violet-500/30",
    text: "text-violet-700 dark:text-violet-300", iconBg: "bg-violet-100 dark:bg-violet-500/20",
    badge: "bg-violet-50 text-violet-700 border-violet-200 dark:bg-violet-500/10 dark:text-violet-300 dark:border-violet-500/30",
  },
  db_query: {
    bg: "bg-emerald-50 dark:bg-emerald-500/10", border: "border-emerald-200 dark:border-emerald-500/30",
    text: "text-emerald-700 dark:text-emerald-300", iconBg: "bg-emerald-100 dark:bg-emerald-500/20",
    badge: "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-500/10 dark:text-emerald-300 dark:border-emerald-500/30",
  },
  web_scrape: {
    bg: "bg-amber-50 dark:bg-amber-500/10", border: "border-amber-200 dark:border-amber-500/30",
    text: "text-amber-700 dark:text-amber-300", iconBg: "bg-amber-100 dark:bg-amber-500/20",
    badge: "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-500/10 dark:text-amber-300 dark:border-amber-500/30",
  },
  custom_function: {
    bg: "bg-rose-50 dark:bg-rose-500/10", border: "border-rose-200 dark:border-rose-500/30",
    text: "text-rose-700 dark:text-rose-300", iconBg: "bg-rose-100 dark:bg-rose-500/20",
    badge: "bg-rose-50 text-rose-700 border-rose-200 dark:bg-rose-500/10 dark:text-rose-300 dark:border-rose-500/30",
  },
};

interface ToolDetailViewProps { toolId: string }

export function ToolDetailView({ toolId }: ToolDetailViewProps) {
  const router = useRouter();
  const { data: tool, isLoading } = useTool(toolId);
  const updateTool = useUpdateTool(toolId);
  const testTool = useTestTool();
  const deleteTool = useDeleteTool();
  const [testInput, setTestInput] = useState('{"query": "test"}');

  const handleConfigChange = useCallback(
    (cfg: Record<string, unknown>) => updateTool.mutate({ config: cfg }),
    [updateTool]
  );
  const handleSchemaChange = useCallback(
    (s: JsonSchema) => updateTool.mutate({ input_schema: s }),
    [updateTool]
  );

  if (isLoading || !tool) {
    return (
      <div className="flex h-full items-center justify-center">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const meta = TOOL_TYPE_META[tool.tool_type];
  const colors = TYPE_COLORS[tool.tool_type];
  const TypeIcon = ICON_MAP[meta?.icon ?? "wrench"] ?? Wrench;

  const handleSave = (field: string, value: unknown) => updateTool.mutate({ [field]: value });
  const handleDelete = () => {
    if (!window.confirm("Delete this tool?")) return;
    deleteTool.mutate(toolId, { onSuccess: () => router.push("/ws/tools") });
  };
  const handleTest = () => {
    try { testTool.mutate({ id: toolId, inputData: JSON.parse(testInput) }); } catch {}
  };

  return (
    <div className="min-h-full bg-background">
      {/* Header */}
      <div className="sticky top-0 z-10 border-b border-border bg-background/80 px-6 py-3 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between">
          <div className="flex items-center gap-3">
            <Link href={"/ws/tools"}>
              <Button variant="ghost" size="icon-sm">
                <ArrowLeft className="h-4 w-4" />
              </Button>
            </Link>
            <div className={cn("flex h-8 w-8 items-center justify-center rounded-lg", colors.iconBg)}>
              <TypeIcon className={cn("h-4 w-4", colors.text)} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-base font-semibold">{tool.name}</h1>
                <Badge className={cn("h-5 px-1.5 text-[10px] border", colors.badge)}>
                  {meta?.label}
                </Badge>
                <StatusBadge tone={tool.is_active ? "active" : "inactive"}>
                  {tool.is_active ? "Active" : "Inactive"}
                </StatusBadge>
                {updateTool.isPending && <Loader2 className="h-3 w-3 animate-spin text-muted-foreground" />}
              </div>
              <p className="text-xs text-muted-foreground">{tool.description?.slice(0, 60)}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline" size="sm" className="gap-1.5"
              onClick={() => updateTool.mutate({ is_active: !tool.is_active })}
            >
              <Power className="h-3.5 w-3.5" />
              {tool.is_active ? "Deactivate" : "Activate"}
            </Button>
            <Button variant="destructive" size="sm" className="gap-1.5" onClick={handleDelete}>
              <Trash2 className="h-3.5 w-3.5" />
            </Button>
          </div>
        </div>
      </div>

      <div className="mx-auto w-full max-w-6xl p-6">
        <div className="grid gap-6 lg:grid-cols-[1fr_360px]">

          {/* Left: config */}
          <div className="space-y-6">
            {/* Basic info */}
            <div className="rounded-xl border border-border bg-card p-5">
              <div className="mb-4 flex items-center gap-2">
                <Info className="h-4 w-4 text-muted-foreground" />
                <h2 className="text-sm font-semibold">Basic Info</h2>
              </div>
              <div className="space-y-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-muted-foreground">Name</label>
                  <Input defaultValue={tool.name} onBlur={(e) => handleSave("name", e.target.value)} />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-muted-foreground">
                    Description <span className="font-normal">(LLM reads this)</span>
                  </label>
                  <Textarea
                    defaultValue={tool.description}
                    onBlur={(e) => handleSave("description", e.target.value)}
                    className="min-h-20 resize-none"
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
                    <Clock className="h-3.5 w-3.5" />
                    Timeout (seconds)
                  </label>
                  <Input
                    type="number" defaultValue={tool.timeout_seconds}
                    onBlur={(e) => handleSave("timeout_seconds", Number(e.target.value))}
                    className="max-w-32"
                  />
                </div>
              </div>
            </div>

            {/* Type-specific config */}
            <div className={cn("rounded-xl border bg-card p-5", colors.border)}>
              <div className="mb-4 flex items-center gap-2">
                <div className={cn("flex h-6 w-6 items-center justify-center rounded-md", colors.iconBg)}>
                  <TypeIcon className={cn("h-3.5 w-3.5", colors.text)} />
                </div>
                <h2 className="text-sm font-semibold">{meta?.label} Configuration</h2>
              </div>
              <ToolConfigRenderer toolType={tool.tool_type} value={tool.config} onChange={handleConfigChange} />
            </div>

            {/* Variables */}
            <div className="rounded-xl border border-border bg-card p-5">
              <div className="mb-3 flex items-center gap-2">
                <Shield className="h-4 w-4 text-primary" />
                <h2 className="text-sm font-semibold">Input Variables</h2>
              </div>
              <VariableSchemaEditor config={tool.config} value={tool.input_schema} onChange={handleSchemaChange} />
            </div>
          </div>

          {/* Right: Test panel */}
          <div className="lg:sticky lg:top-20 lg:h-fit space-y-5">
            <div className="rounded-xl border border-border bg-card p-5">
              <div className="mb-4 flex items-center gap-2">
                <FlaskConical className="h-4 w-4 text-primary" />
                <h2 className="text-sm font-semibold">Test Tool</h2>
              </div>
              <p className="mb-3 text-xs text-muted-foreground">
                Provide input values as JSON matching the variable schema.
              </p>
              <Textarea
                value={testInput}
                onChange={(e) => setTestInput(e.target.value)}
                placeholder='{"query": "test"}'
                className="min-h-28 font-mono text-xs"
              />
              <Button onClick={handleTest} disabled={testTool.isPending} size="sm" className="mt-3 w-full gap-1.5">
                {testTool.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Play className="h-3.5 w-3.5" />}
                Run Test
              </Button>

              {testTool.data && (
                <div className={cn(
                  "mt-4 rounded-lg border p-3",
                  testTool.data.success
                    ? "border-success/40 bg-success/5"
                    : "border-destructive/40 bg-destructive/5"
                )}>
                  <div className="mb-2 flex items-center gap-2">
                    {testTool.data.success
                      ? <CheckCircle2 className="h-4 w-4 text-success" />
                      : <XCircle className="h-4 w-4 text-destructive" />}
                    <span className={cn(
                      "text-xs font-semibold",
                      testTool.data.success ? "text-success" : "text-destructive"
                    )}>
                      {testTool.data.success ? "Success" : "Failed"}
                    </span>
                    <span className="ml-auto flex items-center gap-1 text-[10px] text-muted-foreground">
                      <Clock className="h-2.5 w-2.5" />{testTool.data.latency_ms}ms
                    </span>
                  </div>
                  <pre className="max-h-64 overflow-auto whitespace-pre-wrap break-all rounded-md bg-background/50 p-2 font-mono text-[11px] text-foreground/80">
                    {testTool.data.result || testTool.data.error}
                  </pre>
                </div>
              )}
            </div>

            {/* Tips */}
            <div className={cn("rounded-xl border p-4 text-xs", colors.border, colors.bg)}>
              <div className={cn("flex items-center gap-2 font-medium mb-2", colors.text)}>
                <Terminal className="h-3.5 w-3.5" />
                Quick tips
              </div>
              <ul className={cn("space-y-1.5", colors.text, "opacity-80")}>
                <li className="flex items-start gap-1.5">
                  <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-current" />
                  Changes auto-save when you leave an input field.
                </li>
                <li className="flex items-start gap-1.5">
                  <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-current" />
                  Use the test panel to verify before attaching to an agent.
                </li>
                <li className="flex items-start gap-1.5">
                  <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-current" />
                  Deactivated tools won&apos;t be called by agents.
                </li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
