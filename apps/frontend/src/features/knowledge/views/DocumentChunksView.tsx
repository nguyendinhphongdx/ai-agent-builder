"use client";

import { useState } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  BookOpen,
  FileText,
  Loader2,
  Search,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  useKBChunks,
  useKBDocument,
  useKnowledgeBase,
} from "../hooks/useKnowledge";
import type { KBChunk, KBDocumentDetail } from "../types";

interface DocumentChunksViewProps {
  kbId: string;
  docId: string;
}

const PAGE_SIZE = 20;

export function DocumentChunksView({ kbId, docId }: DocumentChunksViewProps) {
  const [page, setPage] = useState(0);
  const [search, setSearch] = useState("");

  const { data: kb } = useKnowledgeBase(kbId);
  const { data: doc, isLoading: docLoading } = useKBDocument(kbId, docId);
  const { data: chunks, isLoading: chunksLoading } = useKBChunks(
    kbId,
    docId,
    PAGE_SIZE,
    page * PAGE_SIZE,
  );

  const items = chunks?.items ?? [];
  const total = chunks?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const filtered = search.trim()
    ? items.filter((c) => c.content.toLowerCase().includes(search.toLowerCase()))
    : items;

  if (docLoading || !doc) {
    return (
      <div className="flex h-full items-center justify-center text-muted-foreground">
        <Loader2 className="h-5 w-5 animate-spin" />
      </div>
    );
  }

  return (
    <div className="flex h-full">
      {/* Left sidebar (same as KB detail) */}
      <aside className="flex w-64 shrink-0 flex-col border-r border-border bg-muted/30">
        <div className="px-4 pb-2 pt-4">
          <Link
            href={`/ws/knowledge/${kbId}`}
            className="mb-3 inline-flex items-center gap-1.5 text-[11px] font-semibold tracking-wider text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft className="h-3 w-3" />
            KNOWLEDGE
          </Link>
          <div className="flex items-start gap-2.5">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-primary/25 bg-primary/10">
              <BookOpen className="h-4 w-4 text-primary" />
            </div>
            <div className="min-w-0">
              <h2 className="truncate text-sm font-semibold">{kb?.name ?? "Loading…"}</h2>
              <p className="mt-0.5 line-clamp-2 text-[11px] text-muted-foreground">
                {kb?.description || "No description"}
              </p>
            </div>
          </div>
        </div>
        <nav className="mt-2 flex-1 space-y-0.5 px-2">
          <Link
            href={`/ws/knowledge/${kbId}`}
            className="flex w-full items-center gap-2.5 rounded-md bg-accent px-3 py-1.5 text-xs font-medium text-accent-foreground"
          >
            <FileText className="h-3.5 w-3.5" />
            Documents
          </Link>
        </nav>
        <div className="border-t border-border p-4">
          <div className="grid grid-cols-2 gap-2 text-center">
            <Stat label="DOCUMENTS" value={kb?.total_documents ?? 0} />
            <Stat label="LINKED APPS" value={doc.linked_apps} />
          </div>
        </div>
      </aside>

      {/* Main */}
      <div className="flex min-w-0 flex-1 flex-col">
        {/* Header */}
        <div className="flex items-center gap-3 border-b border-border px-6 py-3.5">
          <Link
            href={`/ws/knowledge/${kbId}`}
            className="rounded-md p-1 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
          >
            <ArrowLeft className="h-4 w-4" />
          </Link>
          <FileText className="h-4 w-4 text-muted-foreground" />
          <div className="min-w-0 flex-1">
            <h1 className="truncate text-sm font-medium">{doc.filename}</h1>
            <p className="text-[10px] uppercase tracking-wider text-muted-foreground">
              General chunking
            </p>
          </div>
          <Badge
            variant="secondary"
            className="gap-1 text-[10px] text-emerald-600 dark:text-emerald-400"
          >
            <span className="h-1.5 w-1.5 rounded-full bg-current" />
            {doc.status === "ready" ? "AVAILABLE" : doc.status.toUpperCase()}
          </Badge>
        </div>

        {/* Body: chunks + right panel */}
        <div className="flex min-h-0 flex-1">
          {/* Chunks list */}
          <div className="flex min-w-0 flex-1 flex-col">
            <div className="flex items-center justify-between border-b border-border px-6 py-2.5">
              <p className="text-xs font-semibold">
                {total} CHUNK{total !== 1 && "S"}
              </p>
              <div className="relative w-full max-w-xs">
                <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
                <Input
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search chunks…"
                  className="h-8 pl-7 text-xs"
                />
              </div>
            </div>

            <div className="scrollbar-thin flex-1 overflow-auto p-4">
              {chunksLoading ? (
                <div className="flex h-40 items-center justify-center text-muted-foreground">
                  <Loader2 className="h-5 w-5 animate-spin" />
                </div>
              ) : filtered.length === 0 ? (
                <p className="py-10 text-center text-xs text-muted-foreground">
                  {search ? "Không có chunk khớp search." : "Document chưa có chunk nào."}
                </p>
              ) : (
                <div className="space-y-2.5">
                  {filtered.map((chunk) => (
                    <ChunkCard key={chunk.id} chunk={chunk} />
                  ))}
                </div>
              )}
            </div>

            {/* Pagination */}
            {total > PAGE_SIZE && (
              <div className="flex items-center justify-between border-t border-border px-6 py-2">
                <span className="text-[11px] text-muted-foreground">
                  {page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, total)} of {total}
                </span>
                <div className="flex items-center gap-1">
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7"
                    disabled={page === 0}
                    onClick={() => setPage((p) => Math.max(0, p - 1))}
                  >
                    <ChevronLeft className="h-3.5 w-3.5" />
                  </Button>
                  <span className="px-2 text-[11px] font-mono">
                    {page + 1}/{totalPages}
                  </span>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7"
                    disabled={page + 1 >= totalPages}
                    onClick={() => setPage((p) => p + 1)}
                  >
                    <ChevronRight className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </div>
            )}
          </div>

          {/* Right panel: metadata */}
          <MetadataPanel doc={doc} />
        </div>
      </div>
    </div>
  );
}

/* ─── Chunk card ────────────────────────────────────────────── */

function ChunkCard({ chunk }: { chunk: KBChunk }) {
  const chars = chunk.content.length;
  const idx = String(chunk.chunk_index + 1).padStart(2, "0");
  return (
    <div className="rounded-lg border border-border bg-card/70 p-4 shadow-sm">
      <div className="mb-2 flex items-center justify-between text-[10px] text-muted-foreground">
        <span className="font-mono font-semibold">CHUNK-{idx}</span>
        <div className="flex items-center gap-3 tabular-nums">
          <span>{chars} chars</span>
          {chunk.token_count !== null && <span>{chunk.token_count} tokens</span>}
        </div>
      </div>
      <p className="max-h-64 overflow-auto whitespace-pre-wrap text-xs leading-relaxed text-foreground/90">
        {chunk.content}
      </p>
    </div>
  );
}

/* ─── Right metadata panel ────────────────────────────────── */

function MetadataPanel({ doc }: { doc: KBDocumentDetail }) {
  return (
    <aside className="hidden w-80 shrink-0 flex-col border-l border-border bg-muted/20 lg:flex">
      <div className="scrollbar-thin flex-1 overflow-auto p-4">
        <Section title="DOCUMENT INFORMATION">
          <InfoRow label="Original filename" value={doc.filename} truncate />
          <InfoRow
            label="Original file size"
            value={doc.file_size ? formatSize(doc.file_size) : "—"}
          />
          <InfoRow label="Upload date" value={formatDateTime(doc.created_at)} />
          <InfoRow
            label="Last update"
            value={formatDateTime(doc.processing_completed_at ?? doc.created_at)}
          />
          <InfoRow label="Source" value="Upload File" />
          <InfoRow
            label="MIME type"
            value={<span className="font-mono">{doc.mime_type ?? "—"}</span>}
          />
        </Section>

        <Section title="TECHNICAL PARAMETERS" className="mt-5">
          <InfoRow label="Chunks specification" value="General" />
          <InfoRow
            label="Chunks length"
            value={<span className="font-mono">{doc.chunk_size.toLocaleString()}</span>}
          />
          <InfoRow
            label="Chunk overlap"
            value={<span className="font-mono">{doc.chunk_overlap.toLocaleString()}</span>}
          />
          <InfoRow
            label="Paragraphs"
            value={<span className="font-mono">{doc.chunk_count}</span>}
          />
          <InfoRow
            label="Total tokens"
            value={<span className="font-mono">{(doc.token_count ?? 0).toLocaleString()}</span>}
          />
          <InfoRow
            label="Embedding model"
            value={
              <span className="truncate font-mono text-[10px]">
                {doc.embedding_provider}/{doc.embedding_model}
              </span>
            }
          />
          <InfoRow
            label="Dimensions"
            value={<span className="font-mono">{doc.embedding_dimensions}</span>}
          />
        </Section>

        {doc.error_message && (
          <div className="mt-5 rounded-md border border-destructive/30 bg-destructive/5 p-3">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-destructive">
              Error
            </p>
            <p className="mt-1 text-[11px] text-destructive">{doc.error_message}</p>
          </div>
        )}
      </div>
    </aside>
  );
}

function Section({
  title,
  children,
  className,
}: {
  title: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section className={className}>
      <h4 className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
        {title}
      </h4>
      <div className="space-y-1.5 rounded-md border border-border/60 bg-background/60 p-3">
        {children}
      </div>
    </section>
  );
}

function InfoRow({
  label,
  value,
  truncate,
}: {
  label: string;
  value: React.ReactNode;
  truncate?: boolean;
}) {
  return (
    <div className="flex items-start justify-between gap-3 text-[11px]">
      <span className="shrink-0 text-muted-foreground">{label}</span>
      <span className={cn("text-right", truncate && "min-w-0 truncate")}>
        {value}
      </span>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <div className="text-sm font-semibold">{value.toLocaleString()}</div>
      <div className="text-[10px] tracking-wider text-muted-foreground">{label}</div>
    </div>
  );
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function formatDateTime(iso: string): string {
  const d = new Date(iso);
  return (
    d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }) +
    " " +
    d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
  );
}
