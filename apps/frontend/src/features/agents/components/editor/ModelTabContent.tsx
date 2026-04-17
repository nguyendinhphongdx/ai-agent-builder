"use client";

import { useState, useEffect } from "react";
import { Cpu, Loader2 } from "lucide-react";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { MODEL_OPTIONS } from "../../constants";
import { apiKeyService, type ApiKeyResponse } from "@/lib/api/apiKeyService";
import type { UseFormReturn } from "react-hook-form";
import type { AgentEditorFormValues } from "./types";

interface ModelTabContentProps {
  form: UseFormReturn<AgentEditorFormValues>;
  onApiKeyReady?: (ready: boolean) => void;
}

export function ModelTabContent({ form, onApiKeyReady }: ModelTabContentProps) {
  const watchProvider = form.watch("llm_provider");
  const currentModels = MODEL_OPTIONS[watchProvider]?.models ?? [];

  const [apiKey, setApiKey] = useState("");
  const [savedKey, setSavedKey] = useState<ApiKeyResponse | null>(null);
  const [savingKey, setSavingKey] = useState(false);

  useEffect(() => {
    onApiKeyReady?.(!!savedKey);
  }, [savedKey, onApiKeyReady]);

  // Load saved key when provider changes
  useEffect(() => {
    let cancelled = false;
    apiKeyService
      .list()
      .then((keys) => {
        if (cancelled) return;
        const defaultKey = keys.find(
          (k) => k.provider === watchProvider && k.is_default
        );
        setSavedKey(defaultKey ?? null);
      })
      .catch(() => setSavedKey(null));
    return () => {
      cancelled = true;
    };
  }, [watchProvider]);

  const handleSaveKey = async () => {
    if (!apiKey.trim()) return;
    setSavingKey(true);
    try {
      const result = await apiKeyService.create({
        provider: watchProvider,
        name: `${MODEL_OPTIONS[watchProvider]?.label ?? watchProvider} Key`,
        plaintext_key: apiKey,
        is_default: true,
      });
      setSavedKey(result);
      setApiKey("");
    } catch {
      // TODO: show toast error when toast system is added
    } finally {
      setSavingKey(false);
    }
  };

  return (
    <div className="space-y-5">
      <div>
        <h3 className="text-sm font-semibold">Cấu hình Model</h3>
        <p className="text-xs text-muted-foreground mt-0.5">
          Chọn nhà cung cấp LLM, model và tham số sinh văn bản.
        </p>
      </div>

      <div className="rounded-xl border border-border bg-linear-to-b from-muted/40 to-background p-4">
        <div className="mb-4 flex items-start justify-between gap-3">
          <div className="flex items-start gap-2">
            <div className="mt-0.5 flex h-6 w-6 items-center justify-center rounded-md border border-primary/30 bg-primary/10">
              <Cpu className="h-3.5 w-3.5 text-primary" />
            </div>
            <div>
              <p className="text-sm font-medium">Model Picker</p>
              <p className="text-xs text-muted-foreground mt-0.5">
                Chọn provider và model cho agent hiện tại.
              </p>
            </div>
          </div>
          <Badge variant="secondary" className="text-[11px]">
            {currentModels.length} models
          </Badge>
        </div>

        <div className="space-y-3">
          {/* Provider + Model side by side */}
          <div className="grid grid-cols-2 gap-3">
            <FormField
              control={form.control}
              name="llm_provider"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Nhà cung cấp</FormLabel>
                  <Select
                    onValueChange={(val) => {
                      field.onChange(val);
                      const firstModel = val ? MODEL_OPTIONS[val]?.models[0] : undefined;
                      if (firstModel) {
                        form.setValue("llm_model", firstModel.value);
                      }
                    }}
                    value={field.value}
                  >
                    <FormControl>
                      <SelectTrigger className="h-10 w-full bg-background/80">
                        <SelectValue />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {Object.entries(MODEL_OPTIONS).map(([key, opt]) => (
                        <SelectItem key={key} value={key}>
                          {opt.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="llm_model"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Model</FormLabel>
                  <Select onValueChange={field.onChange} value={field.value}>
                    <FormControl>
                      <SelectTrigger className="h-10 w-full bg-background/80">
                        <SelectValue />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {currentModels.map((m) => (
                        <SelectItem key={m.value} value={m.value}>
                          <div className="flex w-full items-center gap-2">
                            <span>{m.label}</span>
                            <Badge
                              variant="secondary"
                              className="text-[10px] px-1.5 py-0"
                            >
                              {m.context}
                            </Badge>
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </FormItem>
              )}
            />
          </div>

          {/* API Key */}
          <div className="space-y-1.5">
            <label className="text-sm font-medium leading-none">API Key</label>
            {savedKey ? (
              <div className="flex items-center gap-2 rounded-md border border-border bg-background/60 px-3 py-2">
                <span className="flex-1 font-mono text-xs text-muted-foreground">
                  {savedKey.masked_key}
                </span>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="h-6 px-2 text-[11px] text-destructive hover:text-destructive"
                  onClick={async () => {
                    await apiKeyService.remove(savedKey.id);
                    setSavedKey(null);
                  }}
                >
                  Xoá
                </Button>
              </div>
            ) : (
              <div className="flex gap-2">
                <Input
                  type="password"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder={`${MODEL_OPTIONS[watchProvider]?.label ?? "Provider"} API key…`}
                  className="font-mono text-xs bg-background/80"
                  onKeyDown={(e) => e.key === "Enter" && handleSaveKey()}
                />
                <Button
                  type="button"
                  size="sm"
                  disabled={!apiKey.trim() || savingKey}
                  onClick={handleSaveKey}
                  className="shrink-0"
                >
                  {savingKey ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    "Lưu"
                  )}
                </Button>
              </div>
            )}
            <p className="text-[11px] text-muted-foreground">
              {savedKey
                ? "Key đã được mã hóa và lưu vào database."
                : "Nhập API key của provider để kích hoạt preview chat."}
            </p>
          </div>
        </div>
      </div>

      <Separator />

      <div>
        <h4 className="text-sm font-medium">Tham số</h4>
        <p className="text-xs text-muted-foreground mt-0.5">
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
              <span className="text-xs font-mono text-muted-foreground tabular-nums">
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
            <FormDescription>
              Số token tối đa cho mỗi phản hồi.
            </FormDescription>
            <FormControl>
              <Input
                type="number"
                min={1}
                max={128000}
                {...field}
                onChange={(e) => field.onChange(Number(e.target.value))}
              />
            </FormControl>
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
    </div>
  );
}
