"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import {
  BookOpen,
  Plus,
  ExternalLink,
  X,
  Loader2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  useKnowledgeBasesByAgent,
  useDetachKBFromAgent,
} from "@/features/knowledge/hooks/useKnowledge";
import { KnowledgePickerDialog } from "./KnowledgePickerDialog";

interface AgentKBSectionProps {
  agentId?: string;
}

export function AgentKBSection({ agentId }: AgentKBSectionProps) {
  const [pickerOpen, setPickerOpen] = useState(false);
  const { data: kbs = [], isLoading } = useKnowledgeBasesByAgent(agentId ?? "");
  const detach = useDetachKBFromAgent(agentId ?? "");

  const attachedIds = useMemo(() => new Set(kbs.map((k) => k.id)), [kbs]);

  if (!agentId) {
    return (
      <div className="rounded-lg border border-dashed border-border bg-muted/20 p-4 text-center">
        <p className="text-xs text-muted-foreground">
          Lưu agent trước để gắn knowledge.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {isLoading ? (
        <div className="flex h-16 items-center justify-center text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
        </div>
      ) : kbs.length === 0 ? (
        <div className="rounded-lg border border-dashed border-border bg-muted/20 p-5 text-center">
          <BookOpen className="mx-auto mb-2 h-6 w-6 text-muted-foreground/50" />
          <p className="text-xs font-medium">Chưa gắn knowledge nào</p>
          <p className="mt-0.5 text-[11px] text-muted-foreground">
            Gắn KB để agent tra cứu khi trả lời (RAG).
          </p>
          <div className="mt-3 flex items-center justify-center">
            <Button
              type="button"
              size="sm"
              className="gap-1.5 text-xs"
              onClick={() => setPickerOpen(true)}
            >
              <Plus className="h-3 w-3" />
              Pick or create knowledge
            </Button>
          </div>
        </div>
      ) : (
        <div className="space-y-1.5">
          {kbs.map((kb) => (
            <div
              key={kb.id}
              className="flex items-center gap-3 rounded-lg border border-border bg-background/60 px-3 py-2"
            >
              <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md border border-primary/25 bg-primary/10">
                <BookOpen className="h-3.5 w-3.5 text-primary" />
              </div>
              <div className="min-w-0 flex-1">
                <Link
                  href={`/ws/knowledge/${kb.id}`}
                  className="flex items-center gap-1 truncate text-xs font-medium hover:text-primary"
                >
                  {kb.name}
                  <ExternalLink className="h-2.5 w-2.5 shrink-0 opacity-70" />
                </Link>
                <p className="mt-0.5 truncate text-[10px] text-muted-foreground">
                  {kb.total_documents} docs · {kb.total_chunks} chunks
                </p>
              </div>
              <Badge
                variant="secondary"
                className="shrink-0 px-1.5 py-0 text-[9px] font-mono"
              >
                {kb.embedding_provider}
              </Badge>
              <button
                type="button"
                onClick={() => detach.mutate(kb.id)}
                className="shrink-0 rounded p-1 text-muted-foreground/60 transition-colors hover:bg-muted hover:text-destructive"
                title="Gỡ khỏi agent"
              >
                <X className="h-3 w-3" />
              </button>
            </div>
          ))}

          <div className="pt-1">
            <Button
              type="button"
              size="sm"
              variant="outline"
              className="gap-1.5 text-xs"
              onClick={() => setPickerOpen(true)}
            >
              <Plus className="h-3 w-3" />
              Attach or create
            </Button>
          </div>
        </div>
      )}

      <KnowledgePickerDialog
        open={pickerOpen}
        onOpenChange={setPickerOpen}
        agentId={agentId}
        attachedIds={attachedIds}
      />
    </div>
  );
}
