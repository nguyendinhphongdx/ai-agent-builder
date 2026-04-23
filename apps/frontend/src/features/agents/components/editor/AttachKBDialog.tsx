"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { BookOpen, Search, Loader2, Check, Plus } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button, buttonVariants } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { useKnowledgeBases, useAttachKBToAgent } from "@/features/knowledge/hooks/useKnowledge";
import type { KnowledgeBase } from "@/features/knowledge/types";

interface AttachKBDialogProps {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  agentId: string;
  attachedIds: Set<string>;
  onAttached?: () => void;
}

export function AttachKBDialog({
  open,
  onOpenChange,
  agentId,
  attachedIds,
  onAttached,
}: AttachKBDialogProps) {
  const { data: kbs = [], isLoading } = useKnowledgeBases();
  const attach = useAttachKBToAgent(agentId);
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const available = useMemo(
    () =>
      kbs.filter((k) => {
        if (search.trim()) {
          const q = search.toLowerCase();
          return (
            k.name.toLowerCase().includes(q) ||
            (k.description ?? "").toLowerCase().includes(q)
          );
        }
        return true;
      }),
    [kbs, search],
  );

  const toggle = (id: string) => {
    if (attachedIds.has(id)) return;
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleAttach = async () => {
    for (const id of selected) {
      await attach.mutateAsync(id);
    }
    setSelected(new Set());
    onAttached?.();
    onOpenChange(false);
  };

  const canAttach = selected.size > 0 && !attach.isPending;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="flex max-h-[80vh] max-w-2xl flex-col gap-0 p-0">
        <DialogHeader className="border-b border-border px-5 py-3">
          <DialogTitle>Attach knowledge base</DialogTitle>
          <DialogDescription className="text-xs">
            Chọn một hoặc nhiều KB có sẵn để agent truy xuất. Muốn tạo mới →{" "}
            <Link href="/knowledge/new" className="text-primary hover:underline">
              Knowledge
            </Link>
            .
          </DialogDescription>
        </DialogHeader>

        {/* Search */}
        <div className="border-b border-border px-5 py-2.5">
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search knowledge…"
              className="h-8 pl-7 text-xs"
            />
          </div>
        </div>

        {/* List */}
        <div className="scrollbar-thin max-h-[400px] flex-1 overflow-auto p-3">
          {isLoading ? (
            <div className="flex h-40 items-center justify-center text-muted-foreground">
              <Loader2 className="h-5 w-5 animate-spin" />
            </div>
          ) : kbs.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-10 text-center">
              <BookOpen className="mb-2 h-8 w-8 text-muted-foreground/40" />
              <p className="text-sm font-medium">Chưa có knowledge nào</p>
              <p className="mt-1 text-xs text-muted-foreground">
                Tạo KB đầu tiên để gắn vào agent.
              </p>
              <Link
                href="/knowledge/new"
                className={buttonVariants({ size: "sm", className: "mt-4 gap-1.5" })}
              >
                <Plus className="h-3.5 w-3.5" />
                Create Knowledge
              </Link>
            </div>
          ) : available.length === 0 ? (
            <p className="py-10 text-center text-xs text-muted-foreground">
              No matching knowledge.
            </p>
          ) : (
            <div className="space-y-1.5">
              {available.map((kb) => (
                <KBRow
                  key={kb.id}
                  kb={kb}
                  attached={attachedIds.has(kb.id)}
                  selected={selected.has(kb.id)}
                  onToggle={() => toggle(kb.id)}
                />
              ))}
            </div>
          )}
        </div>

        <DialogFooter className="border-t border-border bg-muted/30 px-5 py-3">
          <Button variant="ghost" size="sm" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button size="sm" disabled={!canAttach} onClick={handleAttach}>
            {attach.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : `Attach${selected.size > 0 ? ` (${selected.size})` : ""}`}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/* ─── Row ───────────────────────────────────────────────────── */

function KBRow({
  kb,
  attached,
  selected,
  onToggle,
}: {
  kb: KnowledgeBase;
  attached: boolean;
  selected: boolean;
  onToggle: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onToggle}
      disabled={attached}
      className={cn(
        "flex w-full items-center gap-3 rounded-lg border px-3 py-2.5 text-left transition-colors",
        selected
          ? "border-primary/40 bg-primary/5"
          : attached
          ? "cursor-not-allowed border-border/60 bg-muted/40 opacity-60"
          : "border-border hover:border-primary/40 hover:bg-accent/40",
      )}
    >
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md border border-primary/25 bg-primary/10">
        <BookOpen className="h-4 w-4 text-primary" />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <p className="truncate text-sm font-medium">{kb.name}</p>
          {attached && (
            <Badge variant="secondary" className="shrink-0 px-1 py-0 text-[9px]">
              Attached
            </Badge>
          )}
        </div>
        <p className="mt-0.5 truncate text-[11px] text-muted-foreground">
          {kb.description || "No description"}
        </p>
        <div className="mt-1 flex items-center gap-2 text-[10px] text-muted-foreground">
          <span>{kb.total_documents} docs</span>
          <span>·</span>
          <span>{kb.total_chunks} chunks</span>
          <span>·</span>
          <span className="font-mono">
            {kb.embedding_provider}/{kb.embedding_model}
          </span>
        </div>
      </div>
      {selected && <Check className="h-4 w-4 shrink-0 text-primary" />}
    </button>
  );
}
