"use client";

import { useMemo, useRef, useState } from "react";
import Link from "next/link";
import {
  Plus,
  Search,
  FileText,
  Loader2,
  MoreHorizontal,
  Trash2,
  RotateCcw,
  AlertCircle,
  CheckCircle2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";
import {
  useKBDocuments,
  useUploadDocument,
  useDeleteDocument,
  useReprocessDocument,
} from "../../hooks/useKnowledge";
import type { KBDocument } from "../../types";

interface DocumentsTabProps {
  kbId: string;
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  return `${d.toLocaleDateString()} ${d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`;
}

export function DocumentsTab({ kbId }: DocumentsTabProps) {
  const { data: docs = [], isLoading } = useKBDocuments(kbId);
  const upload = useUploadDocument(kbId);
  const [search, setSearch] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const filtered = useMemo(() => {
    if (!search.trim()) return docs;
    const q = search.toLowerCase();
    return docs.filter((d) => d.filename.toLowerCase().includes(q));
  }, [docs, search]);

  const handlePick = () => fileInputRef.current?.click();
  const handleFiles = (files: FileList | null) => {
    if (!files) return;
    Array.from(files).forEach((f) => upload.mutate(f));
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  return (
    <>
      {/* Header */}
      <div className="flex items-start justify-between border-b border-border px-6 py-4">
        <div>
          <h2 className="text-lg font-semibold">Documents</h2>
          <p className="mt-0.5 text-xs text-muted-foreground">
            Quản lý tài liệu trong knowledge. Mỗi file sẽ được parse, chunk và embed để agent
            truy xuất khi cần.
          </p>
        </div>
        <Button size="sm" className="gap-1.5" onClick={handlePick} disabled={upload.isPending}>
          {upload.isPending ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <Plus className="h-3.5 w-3.5" />
          )}
          Add file
        </Button>
        <input
          ref={fileInputRef}
          type="file"
          hidden
          multiple
          accept=".pdf,.txt,.md,.docx,.csv,.html"
          onChange={(e) => handleFiles(e.target.files)}
        />
      </div>

      {/* Filters */}
      <div className="flex items-center gap-2 border-b border-border px-6 py-2.5">
        <div className="relative w-full max-w-sm">
          <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search documents…"
            className="h-8 pl-7 text-xs"
          />
        </div>
      </div>

      {/* Table */}
      <div className="scrollbar-thin flex-1 overflow-auto">
        {isLoading ? (
          <div className="flex h-64 items-center justify-center text-muted-foreground">
            <Loader2 className="h-5 w-5 animate-spin" />
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex h-64 flex-col items-center justify-center text-center">
            <FileText className="mb-2 h-8 w-8 text-muted-foreground/40" />
            <p className="text-sm font-medium">
              {search ? "No matching document" : "Chưa có document nào"}
            </p>
            <p className="mt-0.5 text-xs text-muted-foreground">
              {search ? "Thử search khác." : "Click \"Add file\" để upload tài liệu đầu tiên."}
            </p>
          </div>
        ) : (
          <table className="w-full table-fixed text-xs">
            <colgroup>
              <col className="w-12" />                          {/* # */}
              <col />                                           {/* Name — fills */}
              <col className="w-24" />                          {/* Chunking */}
              <col className="w-20" />                          {/* Chunks */}
              <col className="w-20" />                          {/* Size */}
              <col className="w-40" />                          {/* Upload Time */}
              <col className="w-44" />                          {/* Status — reserved for phase+progress */}
              <col className="w-14" />                          {/* Action */}
            </colgroup>
            <thead className="sticky top-0 bg-background shadow-[inset_0_-1px_0_0] shadow-border">
              <tr className="text-[10px] uppercase tracking-wider text-muted-foreground">
                <th className="px-6 py-2.5 text-left font-semibold">#</th>
                <th className="px-3 py-2.5 text-left font-semibold">Name</th>
                <th className="px-3 py-2.5 text-left font-semibold">Chunking</th>
                <th className="px-3 py-2.5 text-right font-semibold">Chunks</th>
                <th className="px-3 py-2.5 text-right font-semibold">Size</th>
                <th className="px-3 py-2.5 text-left font-semibold">Upload Time</th>
                <th className="px-3 py-2.5 text-left font-semibold">Status</th>
                <th className="px-3 py-2.5 text-right font-semibold">Action</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((doc, idx) => (
                <DocumentRow key={doc.id} kbId={kbId} doc={doc} index={idx + 1} />
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}

/* ─── Row ──────────────────────────────────────────────────────── */

function DocumentRow({
  kbId,
  doc,
  index,
}: {
  kbId: string;
  doc: KBDocument;
  index: number;
}) {
  const deleteDoc = useDeleteDocument(kbId);
  const reprocessDoc = useReprocessDocument(kbId);
  const isProcessing = doc.status === "pending" || doc.status === "processing";

  return (
    <tr className="border-b border-border/60 transition-colors hover:bg-muted/30">
      <td className="px-6 py-2.5 text-muted-foreground">{index}</td>
      <td className="px-3 py-2.5">
        <Link
          href={`/ws/knowledge/${kbId}/documents/${doc.id}`}
          className="flex items-center gap-2 hover:text-primary"
        >
          <FileText className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
          <span className="truncate font-medium">{doc.filename}</span>
        </Link>
      </td>
      <td className="px-3 py-2.5">
        <Badge variant="secondary" className="h-5 px-2 py-0 text-[10px] uppercase">
          General
        </Badge>
      </td>
      <td className="px-3 py-2.5 text-right font-mono tabular-nums">{doc.chunk_count}</td>
      <td className="px-3 py-2.5 text-right font-mono tabular-nums text-muted-foreground">
        {doc.file_size ? formatSize(doc.file_size) : "—"}
      </td>
      <td className="px-3 py-2.5 text-muted-foreground">{formatDate(doc.created_at)}</td>
      <td className="px-3 py-2.5">
        <StatusBadge doc={doc} />
      </td>
      <td className="px-3 py-2.5 text-right">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="h-7 w-7">
              <MoreHorizontal className="h-3.5 w-3.5" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-36">
            <DropdownMenuItem
              disabled={isProcessing || reprocessDoc.isPending}
              onClick={() => reprocessDoc.mutate(doc.id)}
              className="gap-2 text-xs"
            >
              <RotateCcw className="h-3 w-3" />
              {doc.status === "failed" ? "Retry" : "Re-process"}
            </DropdownMenuItem>
            <DropdownMenuItem
              onClick={() => deleteDoc.mutate(doc.id)}
              className="gap-2 text-xs text-destructive focus:text-destructive"
            >
              <Trash2 className="h-3 w-3" />
              Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </td>
    </tr>
  );
}

const PHASE_LABELS: Record<string, string> = {
  queued: "Queued",
  parsing: "Parsing",
  chunking: "Chunking",
  embedding: "Embedding",
  ready: "Available",
  failed: "Failed",
};

function StatusBadge({ doc }: { doc: KBDocument }) {
  const { status, processing_phase, processing_progress, error_message } = doc;

  if (status === "ready") {
    return (
      <span className="inline-flex items-center gap-1 text-[11px] text-emerald-600 dark:text-emerald-400">
        <CheckCircle2 className="h-3 w-3" />
        Available
      </span>
    );
  }

  if (status === "failed") {
    return (
      <span
        title={error_message ?? ""}
        className={cn(
          "inline-flex items-center gap-1 text-[11px] text-destructive",
          error_message && "cursor-help",
        )}
      >
        <AlertCircle className="h-3 w-3" />
        Failed
      </span>
    );
  }

  // Processing / pending: show phase + optional progress bar
  const phaseLabel = processing_phase
    ? PHASE_LABELS[processing_phase] ?? processing_phase
    : "Pending";
  const showProgress =
    processing_phase === "embedding" &&
    typeof processing_progress === "number" &&
    processing_progress > 0;

  return (
    <div className="flex min-w-[140px] flex-col gap-1">
      <span className="inline-flex items-center gap-1 text-[11px] text-amber-600 dark:text-amber-400">
        <Loader2 className="h-3 w-3 animate-spin" />
        {phaseLabel}
        {showProgress && (
          <span className="font-mono text-[10px] text-muted-foreground">
            {processing_progress}%
          </span>
        )}
      </span>
      {showProgress && (
        <div className="h-1 w-full overflow-hidden rounded-full bg-muted">
          <div
            className="h-full rounded-full bg-amber-500 transition-all"
            style={{ width: `${processing_progress}%` }}
          />
        </div>
      )}
    </div>
  );
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}
