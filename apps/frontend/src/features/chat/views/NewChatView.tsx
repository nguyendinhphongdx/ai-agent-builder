"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowRight, Bot, MessageCircle, Sparkles, Wand2 } from "lucide-react";
import { useAgents } from "@/features/agents/hooks/useAgents";
import { Button, buttonVariants } from "@/components/ui/button";
import { useModelCatalog, findProvider, modelDisplayName, providerOfModel } from "@/lib/models/catalog";
import { cn } from "@/lib/utils";

export function NewChatView() {
  const router = useRouter();
  const { data: agents = [], isLoading } = useAgents();
  const { data: catalog } = useModelCatalog();
  const [selectedAgentId, setSelectedAgentId] = useState("");

  const selectedAgent = useMemo(
    () => agents.find((a) => a.id === selectedAgentId),
    [agents, selectedAgentId]
  );

  const canStart = Boolean(selectedAgentId);
  const featuredAgents = useMemo(() => agents.slice(0, 6), [agents]);

  return (
    <div className="relative flex min-h-[calc(100vh-3rem)] items-center justify-center overflow-hidden bg-linear-to-b from-sky-50/40 via-background to-purple-50/30 dark:from-sky-950/20 dark:via-background dark:to-purple-950/15 px-4 py-8 sm:px-6">
      <div className="pointer-events-none absolute -left-16 top-14 h-60 w-60 rounded-full bg-primary/10 blur-3xl" />
      <div className="pointer-events-none absolute -right-10 bottom-6 h-72 w-72 rounded-full bg-primary/10 blur-3xl" />

      <section className="w-full max-w-4xl rounded-3xl border border-border bg-card/80 p-6 shadow-xl backdrop-blur md:p-8">
        <header className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="inline-flex items-center gap-1 rounded-full border border-sky-200 bg-sky-50 px-2 py-0.5 text-[11px] font-medium text-sky-700 dark:border-sky-500/40 dark:bg-sky-500/10 dark:text-sky-300">
              <Sparkles className="h-3 w-3" />
              Welcome
            </p>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight text-foreground sm:text-4xl">
              Chọn agent, bắt đầu chat ngay
            </h1>
            <p className="mt-2 max-w-2xl text-sm text-muted-foreground sm:text-base">
              Không cần điền form dài. Chỉ chọn một agent phù hợp rồi vào thẳng cuộc trò chuyện.
            </p>
          </div>

          <div className="inline-flex items-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm font-medium text-emerald-700 dark:border-emerald-500/40 dark:bg-emerald-500/10 dark:text-emerald-300">
            <Bot className="h-4 w-4" />
            {agents.length} agent khả dụng
          </div>
        </header>

        <div className="mb-6 rounded-2xl border border-sky-200/70 bg-linear-to-r from-sky-50/80 to-cyan-50/80 p-4 text-sm text-sky-900 dark:border-sky-500/30 dark:from-sky-500/10 dark:to-cyan-500/10 dark:text-sky-200">
          <div className="flex items-center gap-2 font-medium">
            <MessageCircle className="h-4 w-4" />
            Gợi ý nhanh
          </div>
          <p className="mt-1 text-sky-800/90 dark:text-sky-200/90">
            Nếu bạn muốn brainstorm ý tưởng, hãy chọn agent marketing. Nếu cần xử lý tài liệu nội bộ, chọn agent tri thức.
          </p>
        </div>

        {isLoading ? (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="h-24 animate-pulse rounded-2xl border border-border bg-muted/50" />
            ))}
          </div>
        ) : featuredAgents.length > 0 ? (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {featuredAgents.map((agent) => {
              const selected = selectedAgentId === agent.id;
              return (
                <button
                  key={agent.id}
                  type="button"
                  onClick={() => setSelectedAgentId(agent.id)}
                  className={cn(
                    "group rounded-2xl border p-4 text-left transition-all",
                    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500/50",
                    selected
                      ? "border-sky-400 bg-linear-to-br from-sky-50 to-indigo-50 shadow-md shadow-sky-500/15 dark:border-sky-500 dark:from-sky-500/10 dark:to-indigo-500/10"
                      : "border-border bg-card/80 hover:border-sky-300 hover:bg-sky-50/50 dark:hover:border-sky-500/50 dark:hover:bg-sky-500/5"
                  )}
                >
                  <div className="flex items-start justify-between gap-2">
                    <p className="line-clamp-1 font-medium text-foreground">{agent.name}</p>
                    {selected && <Sparkles className="h-4 w-4 text-sky-600 dark:text-sky-300" />}
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {findProvider(catalog?.providers, providerOfModel(agent.model_id))?.label ?? providerOfModel(agent.model_id)} •{" "}
                    {modelDisplayName(catalog?.models, agent.model_id)}
                  </p>
                  {agent.description && (
                    <p className="mt-2 line-clamp-2 text-xs text-muted-foreground">{agent.description}</p>
                  )}
                </button>
              );
            })}
          </div>
        ) : (
          <div className="rounded-2xl border border-dashed border-border bg-muted/30 p-5 text-sm text-muted-foreground">
            Bạn chưa có agent nào. Hãy tạo agent mới để bắt đầu hội thoại.
          </div>
        )}

        <div className="mt-6 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex flex-wrap gap-2">
            <Link
              href="/agents/new"
              className={cn(
                buttonVariants({ variant: "outline", size: "sm" }),
                "gap-1.5 border-sky-300 bg-sky-50/80 text-sky-700 hover:bg-sky-100 dark:border-sky-500/40 dark:bg-sky-500/10 dark:text-sky-300"
              )}
            >
              <Wand2 className="h-3.5 w-3.5" />
              Tạo agent mới
            </Link>
            <Link
              href="/agents"
              className={cn(buttonVariants({ variant: "ghost", size: "sm" }), "gap-1.5")}
            >
              Mở thư viện agent
            </Link>
          </div>

          <Button
            className="h-10 min-w-56 gap-2"
            disabled={!canStart}
            onClick={() => router.push(`/agents/${selectedAgentId}/chat`)}
          >
            Bắt đầu chat{selectedAgent ? ` với ${selectedAgent.name}` : ""}
            <ArrowRight className="h-4 w-4" />
          </Button>
        </div>
      </section>
    </div>
  );
}
