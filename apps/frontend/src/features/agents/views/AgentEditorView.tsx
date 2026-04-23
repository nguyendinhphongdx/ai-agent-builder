"use client";

import { useState, useEffect, useCallback } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import {
  ArrowLeft,
  Save,
  Loader2,
  Bot,
  Cpu,
  Wrench,
  Settings,
  Info,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Form } from "@/components/ui/form";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { BasicInfoCard } from "../components/editor/BasicInfoCard";
import { BehaviorCard } from "../components/editor/BehaviorCard";
import { ModelTabContent } from "../components/editor/ModelTabContent";
import { AdvancedTabContent } from "../components/editor/AdvancedTabContent";
import { AgentKBSection } from "../components/editor/AgentKBSection";
import { ToolsSelector } from "../components/ToolsSelector";
import { AgentPreviewChat } from "../components/AgentPreviewChat";
import { useAgent, useCreateAgent, useUpdateAgent } from "../hooks/useAgents";
import { agentEditorSchema, type AgentEditorFormValues } from "../components/editor/types";
import { BookOpen } from "lucide-react";

/* ─── Tab definitions ──────────────────────────────────────────── */

const tabs = [
  { id: "general", label: "Thông tin", icon: Info },
  { id: "model", label: "Model", icon: Cpu },
  { id: "tools", label: "Công cụ", icon: Wrench },
  { id: "advanced", label: "Nâng cao", icon: Settings },
];

/* ─── Component ──────────────────────────────────────────────────── */

interface AgentEditorViewProps {
  agentId?: string;
}

export function AgentEditorView({ agentId }: AgentEditorViewProps) {
  const isEditMode = !!agentId;
  const { data: agent, isLoading } = useAgent(agentId ?? "");
  const createAgent = useCreateAgent();
  const updateAgent = useUpdateAgent(agentId ?? "");

  const [selectedTools, setSelectedTools] = useState<string[]>([]);
  const [collabMode, setCollabMode] = useState<"none" | "supervisor" | "peer">("none");
  const [pendingAvatarFile, setPendingAvatarFile] = useState<File | null>(null);
  const [workerIds, setWorkerIds] = useState<string[]>([]);
  const [activeTab, setActiveTab] = useState("general");
  const [isCredentialReady, setIsCredentialReady] = useState(false);

  const form = useForm<AgentEditorFormValues>({
    resolver: zodResolver(agentEditorSchema),
    defaultValues: {
      name: "",
      description: "",
      system_prompt: "You are a helpful AI assistant.",
      model_id: "openai/gpt-4o",
      credential_id: null,
      welcome_message: "",
      temperature: 0.7,
      max_tokens: 4096,
      max_turns: 50,
      is_published: false,
    },
  });

  useEffect(() => {
    if (agent) {
      form.reset({
        name: agent.name,
        description: agent.description ?? "",
        system_prompt: agent.system_prompt,
        model_id: agent.model_id,
        credential_id: agent.credential_id,
        welcome_message: agent.welcome_message ?? "",
        temperature: (agent.llm_config?.temperature as number) ?? 0.7,
        max_tokens: (agent.llm_config?.max_tokens as number) ?? 4096,
        max_turns: agent.max_turns ?? 50,
        is_published: agent.is_published ?? false,
      });
    }
  }, [agent, form]);

  const onSubmit = (data: AgentEditorFormValues) => {
    const payload = {
      name: data.name,
      description: data.description,
      system_prompt: data.system_prompt,
      model_id: data.model_id,
      credential_id: data.credential_id,
      welcome_message: data.welcome_message,
      max_turns: data.max_turns,
      is_published: data.is_published,
      llm_config: {
        temperature: data.temperature,
        max_tokens: data.max_tokens,
      },
    };

    if (isEditMode) {
      updateAgent.mutate(payload);
    } else {
      createAgent.mutate(payload, {
        onSuccess: async (created) => {
          // Upload pending avatar after agent is created
          if (pendingAvatarFile) {
            try {
              const { uploadService } = await import("@/lib/api/uploadService");
              const uploaded = await uploadService.upload(pendingAvatarFile, "avatar", {
                entityType: "agent",
                entityId: created.id,
              });
              if (uploaded.url) {
                const { agentService } = await import("../services/agentService");
                await agentService.update(created.id, { avatar_url: uploaded.url });
              }
            } catch {
              // Non-critical, agent is already created
            }
            setPendingAvatarFile(null);
          }
        },
      });
    }
  };

  const handleCredentialReady = useCallback((ready: boolean) => {
    setIsCredentialReady(ready);
  }, []);

  const isPending = createAgent.isPending || updateAgent.isPending;
  const watchName = form.watch("name");
  const watchWelcome = form.watch("welcome_message");

  if (isEditMode && isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="flex h-full">
      {/* ── Left panel - Config ──────────────────────────────────── */}
      <div className="flex w-1/2 flex-col border-r border-border">
        {/* Top bar */}
        <div className="flex items-center justify-between border-b border-border px-4 py-2.5">
          <div className="flex items-center gap-2">
            <Link
              href="/agents"
              className="rounded-md p-1 text-muted-foreground transition-colors hover:text-foreground"
            >
              <ArrowLeft className="h-4 w-4" />
            </Link>
            <Bot className="h-4 w-4 text-primary" />
            <span className="text-sm font-medium">
              {isEditMode ? "Chỉnh sửa Agent" : "Tạo Agent mới"}
            </span>
          </div>
          <Button
            onClick={form.handleSubmit(onSubmit)}
            disabled={isPending}
            size="sm"
            className="gap-1.5"
          >
            {isPending ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Save className="h-3.5 w-3.5" />
            )}
            {isEditMode ? "Lưu" : "Tạo"}
          </Button>
        </div>

        {/* Tabs navigation */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="flex flex-1 flex-col overflow-hidden">
          <div className="border-b border-border px-4">
            <TabsList className="h-10 w-full justify-start gap-0 rounded-none bg-transparent p-0">
              {tabs.map((tab) => (
                <TabsTrigger
                  key={tab.id}
                  value={tab.id}
                  className="relative gap-1.5 rounded-none border-b-2 border-transparent px-3 py-2 text-xs font-medium text-muted-foreground shadow-none transition-none data-[state=active]:border-primary data-[state=active]:bg-transparent data-[state=active]:text-foreground data-[state=active]:shadow-none"
                >
                  <tab.icon className="h-3.5 w-3.5" />
                  {tab.label}
                </TabsTrigger>
              ))}
            </TabsList>
          </div>

          {/* Scrollable content */}
          <div className="scrollbar-thin flex-1 overflow-auto">
            <Form {...form}>
              {/* ── Tab: Thông tin ──────────────────────────────── */}
              <TabsContent value="general" className="mt-0 p-5">
                <div className="space-y-4">
                  <BasicInfoCard
                    form={form}
                    agentId={agentId}
                    currentAvatarUrl={agent?.avatar_url}
                    onAvatarFileReady={setPendingAvatarFile}
                  />
                  <BehaviorCard form={form} />

                  {/* Knowledge base card */}
                  <div className="rounded-xl border border-border bg-linear-to-b from-muted/40 to-background p-4">
                    <div className="mb-4 flex items-start gap-2">
                      <div className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-md border border-primary/30 bg-primary/10">
                        <BookOpen className="h-3.5 w-3.5 text-primary" />
                      </div>
                      <div>
                        <p className="text-sm font-medium">Cơ sở tri thức</p>
                        <p className="text-xs text-muted-foreground mt-0.5">
                          Upload tài liệu để agent truy xuất ngữ nghĩa (RAG).
                        </p>
                      </div>
                    </div>
                    <AgentKBSection agentId={agentId} />
                  </div>
                </div>
              </TabsContent>

              {/* ── Tab: Model ─────────────────────────────────── */}
              <TabsContent value="model" className="mt-0 p-5">
                <ModelTabContent form={form} onCredentialReady={handleCredentialReady} />
              </TabsContent>

              {/* ── Tab: Công cụ ────────────────────────────────── */}
              <TabsContent value="tools" className="mt-0 p-5">
                <div className="space-y-5">
                  <div>
                    <h3 className="text-sm font-semibold">Công cụ</h3>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      Chọn công cụ mà agent có thể sử dụng khi trả lời. Agent sẽ tự quyết định khi nào cần gọi tool.
                    </p>
                  </div>
                  <ToolsSelector
                    selectedToolIds={selectedTools}
                    onToggle={(id) =>
                      setSelectedTools((prev) =>
                        prev.includes(id) ? prev.filter((t) => t !== id) : [...prev, id]
                      )
                    }
                  />
                </div>
              </TabsContent>

              {/* ── Tab: Nâng cao ──────────────────────────────── */}
              <TabsContent value="advanced" className="mt-0 p-5">
                <AdvancedTabContent
                  form={form}
                  agentId={agentId}
                  agent={agent ?? null}
                  collabMode={collabMode}
                  workerIds={workerIds}
                  onCollabModeChange={setCollabMode}
                  onWorkersChange={setWorkerIds}
                />
              </TabsContent>
            </Form>
          </div>
        </Tabs>
      </div>

      {/* ── Right panel - Chat Preview ───────────────────────────── */}
      <div className="w-1/2">
        <AgentPreviewChat
          agentId={agentId}
          agentName={watchName || "Untitled Agent"}
          welcomeMessage={watchWelcome}
          credentialReady={isCredentialReady}
        />
      </div>
    </div>
  );
}
