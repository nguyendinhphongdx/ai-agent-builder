"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  BookOpen,
  Plus,
  Search,
  FileText,
  Loader2,
  MoreHorizontal,
  Trash2,
  Pencil,
} from "lucide-react";
import { Button, buttonVariants } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";
import { useKnowledgeBases, useDeleteKnowledgeBase } from "../hooks/useKnowledge";
import type { KnowledgeBase } from "../types";

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("en-US", { month: "2-digit", day: "2-digit", year: "numeric" });
}

function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

export function KnowledgeListView() {
  const { data: kbs = [], isLoading } = useKnowledgeBases();
  const [search, setSearch] = useState("");

  const filtered = useMemo(() => {
    if (!search.trim()) return kbs;
    const q = search.toLowerCase();
    return kbs.filter(
      (k) =>
        k.name.toLowerCase().includes(q) ||
        (k.description ?? "").toLowerCase().includes(q),
    );
  }, [kbs, search]);

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-6 py-3.5">
        <div className="flex items-center gap-2.5">
          <BookOpen className="h-5 w-5 text-foreground" />
          <h1 className="text-lg font-semibold">Knowledge</h1>
          {!isLoading && (
            <Badge variant="secondary" className="ml-1 px-1.5 py-0 text-[10px]">
              {kbs.length}
            </Badge>
          )}
        </div>
        <Link href={"/ws/knowledge/new"} className={buttonVariants({ size: "sm", className: "gap-1.5" })}>
          <Plus className="h-3.5 w-3.5" />
          Create Knowledge
        </Link>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-2 border-b border-border px-6 py-2.5">
        <div className="relative max-w-sm flex-1">
          <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search knowledge…"
            className="h-8 pl-7 text-xs"
          />
        </div>
      </div>

      {/* Body */}
      <div className="scrollbar-thin flex-1 overflow-auto p-6">
        {isLoading ? (
          <div className="flex h-64 items-center justify-center text-muted-foreground">
            <Loader2 className="h-5 w-5 animate-spin" />
          </div>
        ) : filtered.length === 0 ? (
          <EmptyState hasSearch={!!search.trim()} />
        ) : (
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {filtered.map((kb) => (
              <KBCard key={kb.id} kb={kb} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

/* ─── Card ────────────────────────────────────────────────────────── */

function KBCard({ kb }: { kb: KnowledgeBase }) {
  const router = useRouter();
  const deleteKB = useDeleteKnowledgeBase();
  const [confirming, setConfirming] = useState(false);

  const handleDelete = () => {
    if (confirming) {
      deleteKB.mutate(kb.id);
      setConfirming(false);
    } else {
      setConfirming(true);
      setTimeout(() => setConfirming(false), 3000);
    }
  };

  return (
    <div
      onClick={() => router.push(`/ws/knowledge/${kb.id}`)}
      className={cn(
        "group relative flex cursor-pointer flex-col gap-3 rounded-xl border border-border bg-card/80 p-4 shadow-sm transition-all",
        "hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-md",
      )}
    >
      <div className="flex items-start justify-between">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-primary/25 bg-primary/10">
          <BookOpen className="h-4 w-4 text-primary" />
        </div>
        <div onClick={(e) => e.stopPropagation()}>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7 opacity-0 transition-opacity group-hover:opacity-100"
              >
                <MoreHorizontal className="h-3.5 w-3.5" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-36">
              <DropdownMenuItem
                onClick={() => router.push(`/ws/knowledge/${kb.id}?tab=settings`)}
                className="gap-2 text-xs"
              >
                <Pencil className="h-3 w-3" /> Edit
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={handleDelete}
                className={cn(
                  "gap-2 text-xs",
                  confirming
                    ? "text-destructive focus:text-destructive"
                    : "text-destructive/80 focus:text-destructive",
                )}
              >
                <Trash2 className="h-3 w-3" /> {confirming ? "Click again" : "Delete"}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      <div className="min-h-[2.5rem]">
        <h3 className="line-clamp-1 text-sm font-medium">{kb.name}</h3>
        <p className="mt-0.5 line-clamp-2 text-[11px] leading-relaxed text-muted-foreground">
          {kb.description || "No description"}
        </p>
      </div>

      <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
        <Badge variant="secondary" className="h-5 gap-1 px-1.5 py-0 text-[10px]">
          <FileText className="h-2.5 w-2.5" />
          {formatNumber(kb.total_documents ?? 0)} docs
        </Badge>
        <Badge variant="secondary" className="h-5 px-1.5 py-0 text-[10px]">
          {formatNumber(kb.total_chunks ?? 0)} chunks
        </Badge>
      </div>

      <div className="flex items-center justify-between border-t border-border/50 pt-2 text-[10px] text-muted-foreground">
        <span className="truncate font-mono">
          {kb.embedding_provider}/{kb.embedding_model}
        </span>
        <span>{formatDate(kb.updated_at)}</span>
      </div>
    </div>
  );
}

/* ─── Empty state ────────────────────────────────────────────────── */

function EmptyState({ hasSearch }: { hasSearch: boolean }) {
  return (
    <div className="flex h-64 flex-col items-center justify-center text-center">
      <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-2xl border border-border bg-muted">
        <BookOpen className="h-5 w-5 text-muted-foreground" />
      </div>
      {hasSearch ? (
        <>
          <p className="text-sm font-medium">No matching knowledge</p>
          <p className="mt-0.5 text-xs text-muted-foreground">Try a different search term.</p>
        </>
      ) : (
        <>
          <p className="text-sm font-medium">Chưa có knowledge nào</p>
          <p className="mt-0.5 text-xs text-muted-foreground">
            Tạo knowledge đầu tiên để agent có thể truy xuất tài liệu (RAG).
          </p>
          <Link
            href={"/ws/knowledge/new"}
            className={buttonVariants({ size: "sm", className: "mt-4 gap-1.5" })}
          >
            <Plus className="h-3.5 w-3.5" />
            Create Knowledge
          </Link>
        </>
      )}
    </div>
  );
}
