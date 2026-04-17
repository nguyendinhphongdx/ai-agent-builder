"use client";

import { Users, Settings, Info } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import {
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
} from "@/components/ui/form";
import { MultiAgentSection } from "../MultiAgentSection";
import type { UseFormReturn } from "react-hook-form";
import type { AgentEditorFormValues } from "./types";

type CollabMode = "none" | "supervisor" | "peer";

interface AdvancedTabContentProps {
  form: UseFormReturn<AgentEditorFormValues>;
  agentId?: string;
  agent?: {
    id: string;
    status: string;
    created_at: string;
    updated_at: string;
  } | null;
  collabMode: CollabMode;
  workerIds: string[];
  onCollabModeChange: (mode: CollabMode) => void;
  onWorkersChange: (ids: string[]) => void;
}

export function AdvancedTabContent({
  form,
  agentId,
  agent,
  collabMode,
  workerIds,
  onCollabModeChange,
  onWorkersChange,
}: AdvancedTabContentProps) {
  const isEditMode = !!agentId;

  return (
    <div className="space-y-4">
      {/* Multi-Agent */}
      <div className="rounded-xl border border-border bg-linear-to-b from-muted/40 to-background p-4">
        <div className="mb-4 flex items-start gap-2">
          <div className="mt-0.5 flex h-6 w-6 items-center justify-center rounded-md border border-primary/30 bg-primary/10">
            <Users className="h-3.5 w-3.5 text-primary" />
          </div>
          <div>
            <p className="text-sm font-medium">Đa agent (Multi-Agent)</p>
            <p className="text-xs text-muted-foreground mt-0.5">
              Kết hợp nhiều agent cộng tác để xử lý task phức tạp.
            </p>
          </div>
        </div>
        <MultiAgentSection
          currentAgentId={agentId}
          mode={collabMode}
          workerIds={workerIds}
          onModeChange={onCollabModeChange}
          onWorkersChange={onWorkersChange}
        />
      </div>

      {/* Publish */}
      <div className="rounded-xl border border-border bg-linear-to-b from-muted/40 to-background p-4">
        <div className="mb-4 flex items-start gap-2">
          <div className="mt-0.5 flex h-6 w-6 items-center justify-center rounded-md border border-primary/30 bg-primary/10">
            <Settings className="h-3.5 w-3.5 text-primary" />
          </div>
          <div>
            <p className="text-sm font-medium">Phân quyền & Xuất bản</p>
            <p className="text-xs text-muted-foreground mt-0.5">
              Quản lý trạng thái xuất bản và quyền truy cập agent.
            </p>
          </div>
        </div>

        <FormField
          control={form.control}
          name="is_published"
          render={({ field }) => (
            <FormItem>
              <div className="flex items-center justify-between rounded-lg border border-border bg-background/60 px-4 py-3">
                <div className="space-y-0.5">
                  <FormLabel className="text-sm">Xuất bản Agent</FormLabel>
                  <FormDescription className="text-xs">
                    Agent xuất bản sẽ hiển thị trong thư viện cho mọi người sử
                    dụng.
                  </FormDescription>
                </div>
                <FormControl>
                  <Switch
                    checked={field.value}
                    onCheckedChange={field.onChange}
                  />
                </FormControl>
              </div>
            </FormItem>
          )}
        />
      </div>

      {/* System info (edit mode) */}
      {isEditMode && agent && (
        <div className="rounded-xl border border-border bg-linear-to-b from-muted/40 to-background p-4">
          <div className="mb-3 flex items-start gap-2">
            <div className="mt-0.5 flex h-6 w-6 items-center justify-center rounded-md border border-border bg-muted/60">
              <Info className="h-3.5 w-3.5 text-muted-foreground" />
            </div>
            <div>
              <p className="text-sm font-medium">Thông tin hệ thống</p>
              <p className="text-xs text-muted-foreground mt-0.5">
                Metadata chỉ đọc của agent.
              </p>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="rounded-lg border border-border bg-background/60 p-3">
              <p className="text-muted-foreground">Agent ID</p>
              <p className="mt-0.5 break-all font-mono text-[11px]">
                {agent.id}
              </p>
            </div>
            <div className="rounded-lg border border-border bg-background/60 p-3">
              <p className="text-muted-foreground">Trạng thái</p>
              <Badge
                variant={agent.status === "active" ? "default" : "secondary"}
                className="mt-1"
              >
                {agent.status}
              </Badge>
            </div>
            <div className="rounded-lg border border-border bg-background/60 p-3">
              <p className="text-muted-foreground">Ngày tạo</p>
              <p className="mt-0.5">
                {new Date(agent.created_at).toLocaleDateString("vi-VN")}
              </p>
            </div>
            <div className="rounded-lg border border-border bg-background/60 p-3">
              <p className="text-muted-foreground">Cập nhật lần cuối</p>
              <p className="mt-0.5">
                {new Date(agent.updated_at).toLocaleDateString("vi-VN")}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
