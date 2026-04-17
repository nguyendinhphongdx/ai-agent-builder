"use client";

import Link from "next/link";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import {
  ArrowLeft, Globe, Code, Database, Wrench, Search, Loader2, Info,
  Zap, Shield, Clock, Sparkles,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Separator } from "@/components/ui/separator";
import {
  Form, FormControl, FormField, FormItem, FormLabel, FormMessage,
} from "@/components/ui/form";
import { useCreateTool } from "../hooks/useTools";
import { TOOL_TYPE_META, type JsonSchema, type ToolType } from "../types";
import { ToolConfigRenderer } from "../components/ToolConfigRenderer";
import { VariableSchemaEditor } from "../components/VariableSchemaEditor";
import { cn } from "@/lib/utils";

const ICON_MAP: Record<string, React.ElementType> = {
  globe: Globe, code: Code, database: Database, wrench: Wrench, spider: Search,
};

const TYPE_COLORS: Record<ToolType, { bg: string; border: string; text: string; iconBg: string }> = {
  http_request: {
    bg: "bg-blue-50 dark:bg-blue-500/10",
    border: "border-blue-200 dark:border-blue-500/30",
    text: "text-blue-700 dark:text-blue-300",
    iconBg: "bg-blue-100 dark:bg-blue-500/20",
  },
  code_exec: {
    bg: "bg-violet-50 dark:bg-violet-500/10",
    border: "border-violet-200 dark:border-violet-500/30",
    text: "text-violet-700 dark:text-violet-300",
    iconBg: "bg-violet-100 dark:bg-violet-500/20",
  },
  db_query: {
    bg: "bg-emerald-50 dark:bg-emerald-500/10",
    border: "border-emerald-200 dark:border-emerald-500/30",
    text: "text-emerald-700 dark:text-emerald-300",
    iconBg: "bg-emerald-100 dark:bg-emerald-500/20",
  },
  web_scrape: {
    bg: "bg-amber-50 dark:bg-amber-500/10",
    border: "border-amber-200 dark:border-amber-500/30",
    text: "text-amber-700 dark:text-amber-300",
    iconBg: "bg-amber-100 dark:bg-amber-500/20",
  },
  custom_function: {
    bg: "bg-rose-50 dark:bg-rose-500/10",
    border: "border-rose-200 dark:border-rose-500/30",
    text: "text-rose-700 dark:text-rose-300",
    iconBg: "bg-rose-100 dark:bg-rose-500/20",
  },
};

function getDefaultConfig(type: ToolType): Record<string, unknown> {
  switch (type) {
    case "http_request":
      return { method: "GET", url: "", headers: {}, params: {}, body_template: "", auth_type: "none" };
    case "code_exec":
      return { language: "python", code_template: "def run(inputs):\n    return inputs\n" };
    case "web_scrape":
      return { url_template: "", max_length: 5000, css_selector: "", extract_type: "text", wait_for_js: false };
    case "db_query":
      return { connection_string: "", query_template: "SELECT * FROM {table_name} LIMIT {limit};", max_rows: 50 };
    case "custom_function":
      return { function_code: "def run(inputs):\n    return inputs\n" };
  }
}

function getDefaultSchema(): JsonSchema {
  return { type: "object", properties: {}, required: [] };
}

const schema = z.object({
  name: z.string().min(1, "Name is required"),
  description: z.string().min(1, "Description is required"),
  tool_type: z.enum(["http_request", "code_exec", "db_query", "web_scrape", "custom_function"]),
  timeout_seconds: z.number().int().min(1).max(300),
});
type FormValues = z.infer<typeof schema>;

export function ToolCreateView() {
  const router = useRouter();
  const createTool = useCreateTool();
  const [selectedType, setSelectedType] = useState<ToolType>("http_request");
  const [config, setConfig] = useState<Record<string, unknown>>(getDefaultConfig("http_request"));
  const [inputSchema, setInputSchema] = useState<JsonSchema>(getDefaultSchema());

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { name: "", description: "", tool_type: "http_request", timeout_seconds: 30 },
  });

  const onTypeChange = (type: ToolType) => {
    setSelectedType(type);
    form.setValue("tool_type", type, { shouldDirty: true });
    setConfig(getDefaultConfig(type));
    setInputSchema(getDefaultSchema());
  };

  const onSubmit = (values: FormValues) => {
    createTool.mutate(
      { ...values, config, input_schema: inputSchema },
      { onSuccess: (created) => router.push(`/tools/${created.id}`) }
    );
  };

  const colors = TYPE_COLORS[selectedType];

  return (
    <div className="min-h-full bg-background">
      {/* Header */}
      <div className="border-b border-border bg-background/80 px-6 py-3 backdrop-blur sticky top-0 z-10">
        <div className="mx-auto flex max-w-6xl items-center justify-between">
          <div className="flex items-center gap-3">
            <Link href="/tools">
              <Button variant="ghost" size="icon-sm">
                <ArrowLeft className="h-4 w-4" />
              </Button>
            </Link>
            <div>
              <h1 className="text-lg font-semibold">Create Tool</h1>
              <p className="text-xs text-muted-foreground">
                Choose a type, configure it, and the LLM can call it automatically.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Link href="/tools">
              <Button variant="outline" size="sm">Cancel</Button>
            </Link>
            <Button
              onClick={form.handleSubmit(onSubmit)}
              disabled={createTool.isPending}
              size="sm"
              className="gap-1.5"
            >
              {createTool.isPending ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Sparkles className="h-3.5 w-3.5" />
              )}
              Create Tool
            </Button>
          </div>
        </div>
      </div>

      <div className="mx-auto w-full max-w-6xl p-6">
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">

            {/* Tool type picker */}
            <div className="rounded-xl border border-border bg-card p-5">
              <div className="mb-4 flex items-center gap-2">
                <Zap className="h-4 w-4 text-primary" />
                <h2 className="text-sm font-semibold">Tool Type</h2>
              </div>
              <div className="grid gap-3 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5">
                {(Object.entries(TOOL_TYPE_META) as [ToolType, (typeof TOOL_TYPE_META)[ToolType]][]).map(
                  ([type, meta]) => {
                    const Icon = ICON_MAP[meta.icon] ?? Wrench;
                    const selected = selectedType === type;
                    const tc = TYPE_COLORS[type];
                    return (
                      <button
                        key={type}
                        type="button"
                        onClick={() => onTypeChange(type)}
                        className={cn(
                          "rounded-xl border p-4 text-left transition-all",
                          selected
                            ? cn(tc.bg, tc.border, "shadow-sm ring-1", tc.border)
                            : "border-border hover:border-border hover:bg-muted/50"
                        )}
                      >
                        <div className={cn(
                          "mb-3 inline-flex h-9 w-9 items-center justify-center rounded-lg",
                          selected ? tc.iconBg : "bg-muted"
                        )}>
                          <Icon className={cn("h-4 w-4", selected ? tc.text : "text-muted-foreground")} />
                        </div>
                        <p className={cn("text-xs font-semibold", selected ? tc.text : "text-foreground")}>
                          {meta.label}
                        </p>
                        <p className="mt-1 text-[11px] leading-relaxed text-muted-foreground">
                          {meta.description}
                        </p>
                      </button>
                    );
                  }
                )}
              </div>
            </div>

            {/* Main config */}
            <div className="grid gap-6 lg:grid-cols-[1fr_340px]">

              {/* Left: Basic info + type config */}
              <div className="space-y-6">
                {/* Basic info */}
                <div className="rounded-xl border border-border bg-card p-5">
                  <div className="mb-4 flex items-center gap-2">
                    <Info className="h-4 w-4 text-muted-foreground" />
                    <h2 className="text-sm font-semibold">Basic Info</h2>
                  </div>

                  <div className="space-y-4">
                    <FormField
                      control={form.control}
                      name="name"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Name</FormLabel>
                          <FormControl>
                            <Input placeholder="e.g. Search Products API" {...field} />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />

                    <FormField
                      control={form.control}
                      name="description"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>
                            Description{" "}
                            <span className="font-normal text-muted-foreground">
                              (LLM reads this to decide when to call the tool)
                            </span>
                          </FormLabel>
                          <FormControl>
                            <Textarea
                              className="min-h-20 resize-none"
                              placeholder="Explain what this tool does, when to use it, and what it returns."
                              {...field}
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />

                    <FormField
                      control={form.control}
                      name="timeout_seconds"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel className="flex items-center gap-1.5">
                            <Clock className="h-3.5 w-3.5 text-muted-foreground" />
                            Timeout (seconds)
                          </FormLabel>
                          <FormControl>
                            <Input
                              type="number"
                              min={1}
                              max={300}
                              className="max-w-32"
                              value={field.value}
                              onChange={(e) => field.onChange(Number(e.target.value))}
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  </div>
                </div>

                {/* Type-specific config */}
                <div className={cn("rounded-xl border bg-card p-5", colors.border)}>
                  <div className="mb-4 flex items-center gap-2">
                    <div className={cn("flex h-6 w-6 items-center justify-center rounded-md", colors.iconBg)}>
                      {(() => {
                        const Icon = ICON_MAP[TOOL_TYPE_META[selectedType].icon] ?? Wrench;
                        return <Icon className={cn("h-3.5 w-3.5", colors.text)} />;
                      })()}
                    </div>
                    <h2 className="text-sm font-semibold">
                      {TOOL_TYPE_META[selectedType].label} Configuration
                    </h2>
                  </div>
                  <ToolConfigRenderer
                    toolType={selectedType}
                    value={config}
                    onChange={setConfig}
                  />
                </div>
              </div>

              {/* Right: Variables + tips */}
              <div className="space-y-4 lg:sticky lg:top-20 lg:h-fit">
                <div className="rounded-xl border border-border bg-card p-5">
                  <div className="mb-3 flex items-center gap-2">
                    <Shield className="h-4 w-4 text-primary" />
                    <h2 className="text-sm font-semibold">Input Variables</h2>
                  </div>
                  <VariableSchemaEditor
                    config={config}
                    value={inputSchema}
                    onChange={setInputSchema}
                  />
                </div>

                <div className={cn(
                  "flex items-start gap-2.5 rounded-xl border p-4 text-xs",
                  colors.border, colors.bg
                )}>
                  <Info className={cn("mt-0.5 h-4 w-4 shrink-0", colors.text)} />
                  <div className={cn("space-y-1", colors.text)}>
                    <p className="font-medium">How variables work</p>
                    <p className="opacity-80">
                      Variables like <code className="rounded bg-background/50 px-1 py-0.5 font-mono text-[10px]">
                        {"{query}"}
                      </code> detected from your config appear above.
                      Add descriptions so the LLM knows what values to pass.
                    </p>
                  </div>
                </div>

                <div className="rounded-xl border border-border bg-muted/30 p-4 text-xs text-muted-foreground space-y-2">
                  <p className="font-medium text-foreground">Tips</p>
                  <ul className="space-y-1.5">
                    <li className="flex items-start gap-1.5">
                      <span className="mt-1 h-1 w-1 shrink-0 rounded-full bg-primary" />
                      Write clear descriptions — the LLM uses them to decide when to call this tool.
                    </li>
                    <li className="flex items-start gap-1.5">
                      <span className="mt-1 h-1 w-1 shrink-0 rounded-full bg-primary" />
                      Use {"{variable}"} placeholders in URLs and templates.
                    </li>
                    <li className="flex items-start gap-1.5">
                      <span className="mt-1 h-1 w-1 shrink-0 rounded-full bg-primary" />
                      Test your tool after creating it to verify it works.
                    </li>
                  </ul>
                </div>
              </div>
            </div>
          </form>
        </Form>
      </div>
    </div>
  );
}
