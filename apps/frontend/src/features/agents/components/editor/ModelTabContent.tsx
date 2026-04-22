"use client";

import { useState, useEffect, useCallback } from "react";
import { Cpu, Sparkles, ChevronRight, Lock } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Slider } from "@/components/ui/slider";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";
import {
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
} from "@/components/ui/form";
import type { UseFormReturn } from "react-hook-form";
import {
  aiCredentialService,
  type AICredentialResponse,
} from "@/lib/api/aiCredentialService";
import {
  getModelById,
  getProvider,
  providerOfModel,
} from "@/lib/models/catalog";
import { ModelPickerDialog } from "./ModelPickerDialog";
import type { AgentEditorFormValues } from "./types";

interface ModelTabContentProps {
  form: UseFormReturn<AgentEditorFormValues>;
  onCredentialReady?: (ready: boolean) => void;
}

export function ModelTabContent({ form, onCredentialReady }: ModelTabContentProps) {
  const modelId = form.watch("model_id");
  const credentialId = form.watch("credential_id");

  const [credentials, setCredentials] = useState<AICredentialResponse[]>([]);
  const [pickerOpen, setPickerOpen] = useState(false);

  const loadCredentials = useCallback(async () => {
    try {
      const list = await aiCredentialService.list();
      setCredentials(list);
      return list;
    } catch {
      setCredentials([]);
      return [];
    }
  }, []);

  useEffect(() => {
    loadCredentials();
  }, [loadCredentials]);

  // Let parent know whether a usable credential is linked (drives preview chat enablement)
  useEffect(() => {
    onCredentialReady?.(!!credentialId);
  }, [credentialId, onCredentialReady]);

  const selectedModel = getModelById(modelId);
  const provider = providerOfModel(modelId);
  const selectedCredential = credentials.find((c) => c.id === credentialId) ?? null;

  const handleSelect = (newModelId: string, newCredentialId: string) => {
    form.setValue("model_id", newModelId, { shouldDirty: true });
    form.setValue("credential_id", newCredentialId, { shouldDirty: true });
  };

  const handleCredentialCreated = async (cred: AICredentialResponse) => {
    await loadCredentials();
    // If the new credential matches current model's provider and no credential is linked, auto-link it
    if (cred.provider === provider && !credentialId) {
      form.setValue("credential_id", cred.id, { shouldDirty: true });
    }
  };

  return (
    <div className="space-y-5">
      <div>
        <h3 className="text-sm font-semibold">Cấu hình Model</h3>
        <p className="mt-0.5 text-xs text-muted-foreground">
          Chọn model và credential sẽ được dùng để chạy agent.
        </p>
      </div>

      {/* Model selector card */}
      <div className="rounded-xl border border-border bg-linear-to-b from-muted/40 to-background p-4">
        <div className="mb-3 flex items-start gap-2">
          <div className="mt-0.5 flex h-6 w-6 items-center justify-center rounded-md border border-primary/30 bg-primary/10">
            <Cpu className="h-3.5 w-3.5 text-primary" />
          </div>
          <div>
            <p className="text-sm font-medium">Model</p>
            <p className="mt-0.5 text-xs text-muted-foreground">
              Mở dialog để chọn từ catalog đầy đủ.
            </p>
          </div>
        </div>

        {/* Selected model tile — click to reopen picker */}
        <button
          type="button"
          onClick={() => setPickerOpen(true)}
          className="group flex w-full items-center gap-3 rounded-lg border border-border bg-background/80 px-3 py-2.5 text-left transition-colors hover:border-primary/50 hover:bg-accent/30"
        >
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md border border-border bg-muted">
            <Sparkles className="h-4 w-4 text-muted-foreground" />
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium">
              {selectedModel?.name ?? modelId}
            </p>
            <p className="truncate text-[11px] text-muted-foreground">
              {getProvider(provider)?.label ?? provider}
              {selectedCredential && (
                <>
                  {" • "}
                  <span className="font-mono">{selectedCredential.masked_key}</span>
                </>
              )}
            </p>
          </div>
          <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground transition-colors group-hover:text-foreground" />
        </button>

        {/* Missing credential warning */}
        {!selectedCredential && (
          <div className="mt-2 flex items-start gap-2 rounded-md border border-amber-500/30 bg-amber-500/5 px-3 py-2">
            <Lock className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-500" />
            <div className="flex-1">
              <p className="text-[11px] font-medium text-amber-600 dark:text-amber-400">
                Chưa có credential
              </p>
              <p className="text-[11px] text-muted-foreground">
                Agent sẽ không chạy được cho đến khi bạn kết nối credential cho{" "}
                {getProvider(provider)?.label ?? provider}.
              </p>
            </div>
            <Button
              type="button"
              size="sm"
              variant="outline"
              className="h-6 shrink-0 px-2 text-[11px]"
              onClick={() => setPickerOpen(true)}
            >
              Connect
            </Button>
          </div>
        )}
      </div>

      <Separator />

      <div>
        <h4 className="text-sm font-medium">Tham số</h4>
        <p className="mt-0.5 text-xs text-muted-foreground">
          Điều chỉnh hành vi sinh văn bản của model.
        </p>
      </div>

      {/* Temperature */}
      <FormField
        control={form.control}
        name="temperature"
        render={({ field }) => (
          <FormItem>
            <div className="flex items-center justify-between">
              <FormLabel>Temperature</FormLabel>
              <span className="font-mono text-xs tabular-nums text-muted-foreground">
                {(field.value ?? 0.7).toFixed(1)}
              </span>
            </div>
            <FormDescription>
              Thấp = chính xác hơn. Cao = sáng tạo hơn.
            </FormDescription>
            <FormControl>
              <Slider
                min={0}
                max={2}
                step={0.1}
                value={[field.value ?? 0.7]}
                onValueChange={(vals) => field.onChange(vals[0])}
              />
            </FormControl>
            <div className="flex justify-between text-[10px] text-muted-foreground">
              <span>Chính xác</span>
              <span>Sáng tạo</span>
            </div>
          </FormItem>
        )}
      />

      {/* Max Tokens */}
      <FormField
        control={form.control}
        name="max_tokens"
        render={({ field }) => (
          <FormItem>
            <FormLabel>Max Tokens</FormLabel>
            <FormDescription>Số token tối đa cho mỗi phản hồi.</FormDescription>
            <FormControl>
              <Input
                type="number"
                min={1}
                max={selectedModel?.max_output ?? 128000}
                {...field}
                onChange={(e) => field.onChange(Number(e.target.value))}
              />
            </FormControl>
            {selectedModel && (
              <p className="text-[10px] text-muted-foreground">
                {selectedModel.name} hỗ trợ tối đa{" "}
                <Badge variant="secondary" className="px-1 py-0 text-[9px]">
                  {selectedModel.max_output.toLocaleString()} tokens
                </Badge>
              </p>
            )}
          </FormItem>
        )}
      />

      {/* Max Turns */}
      <FormField
        control={form.control}
        name="max_turns"
        render={({ field }) => (
          <FormItem>
            <FormLabel>Giới hạn lượt hội thoại</FormLabel>
            <FormDescription>
              Số lượt trao đổi tối đa trong một cuộc hội thoại.
            </FormDescription>
            <FormControl>
              <Input
                type="number"
                min={1}
                max={200}
                {...field}
                onChange={(e) => field.onChange(Number(e.target.value))}
              />
            </FormControl>
          </FormItem>
        )}
      />

      {/* Model picker dialog */}
      <ModelPickerDialog
        open={pickerOpen}
        onOpenChange={setPickerOpen}
        value={modelId}
        credentialId={credentialId}
        credentials={credentials}
        onSelect={handleSelect}
        onCredentialCreated={handleCredentialCreated}
      />
    </div>
  );
}
