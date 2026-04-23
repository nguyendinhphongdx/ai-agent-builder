"use client";

import { useMemo, useState, useRef } from "react";
import {
  BookOpen,
  Search,
  Check,
  Plus,
  FileText,
  Loader2,
  CheckCircle2,
  AlertCircle,
  UploadCloud,
} from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";
import {
  useKnowledgeBases,
  useKBDocuments,
  useUploadDocument,
  useAttachKBToAgent,
} from "@/features/knowledge/hooks/useKnowledge";
import type { KBDocument, KnowledgeBase } from "@/features/knowledge/types";
import { QuickCreateKBDialog } from "./QuickCreateKBDialog";

interface KnowledgePickerDialogProps {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  agentId: string;
  attachedIds: Set<string>;
}

export function KnowledgePickerDialog(props: KnowledgePickerDialogProps) {
  return (
    <Dialog open={props.open} onOpenChange={props.onOpenChange}>
      {props.open && <PickerBody {...props} />}
    </Dialog>
  );
}

/* ─── Body ───────────────────────────────────────────────────── */

function PickerBody({
  onOpenChange,
  agentId,
  attachedIds,
}: KnowledgePickerDialogProps) {
  const { data: kbs = [], isLoading } = useKnowledgeBases();
  const attach = useAttachKBToAgent(agentId);

  const [search, setSearch] = useState("");
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [highlightId, setHighlightId] = useState<string | null>(null);
  const [excludedProviders, setExcludedProviders] = useState<Set<string>>(new Set());
  const [filterDocs, setFilterDocs] = useState<"any" | "has" | "empty">("any");
  const [createOpen, setCreateOpen] = useState(false);

  // Providers present in the user's KBs — filter by these
  const providers = useMemo(() => {
    const set = new Set<string>();
    kbs.forEach((k) => set.add(k.embedding_provider));
    return Array.from(set).sort();
  }, [kbs]);

  const filtered = useMemo(() => {
    return kbs.filter((k) => {
      if (excludedProviders.has(k.embedding_provider)) return false;
      if (filterDocs === "has" && (k.total_documents ?? 0) === 0) return false;
      if (filterDocs === "empty" && (k.total_documents ?? 0) > 0) return false;
      if (search.trim()) {
        const q = search.toLowerCase();
        if (
          !k.name.toLowerCase().includes(q) &&
          !(k.description ?? "").toLowerCase().includes(q)
        ) {
          return false;
        }
      }
      return true;
    });
  }, [kbs, excludedProviders, filterDocs, search]);

  const highlighted = useMemo(
    () => kbs.find((k) => k.id === highlightId) ?? null,
    [kbs, highlightId],
  );

  const toggleProvider = (p: string) => {
    setExcludedProviders((prev) => {
      const next = new Set(prev);
      if (next.has(p)) next.delete(p);
      else next.add(p);
      return next;
    });
  };

  const toggleSelect = (id: string) => {
    if (attachedIds.has(id)) return;
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleAttach = async () => {
    for (const id of selectedIds) {
      await attach.mutateAsync(id);
    }
    onOpenChange(false);
  };

  const handleCreated = async (kb: KnowledgeBase) => {
    // Auto-attach the newly-created KB + check it for visibility
    await attach.mutateAsync(kb.id);
    setSelectedIds((prev) => new Set(prev).add(kb.id));
    setHighlightId(kb.id);
  };

  return (
    <>
      <DialogContent
        className="flex h-[85vh] max-h-[800px] w-[95vw] max-w-[1200px] flex-col gap-0 p-0 sm:max-w-[1200px]"
        showCloseButton={false}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border px-5 py-3">
          <div>
            <DialogTitle>Select Knowledge for your Agent</DialogTitle>
            <DialogDescription className="mt-0.5 text-xs">
              Chọn knowledge đã có hoặc tạo mới. Có thể upload file trực tiếp ở panel bên phải.
            </DialogDescription>
          </div>
        </div>

        {/* Body: filters | list | detail */}
        <div className="grid min-h-0 flex-1 grid-cols-[220px_1fr_360px]">
          {/* ── Filters ────────────────────────────────────── */}
          <div className="flex flex-col overflow-y-auto border-r border-border p-4">
            <h4 className="mb-3 text-xs font-semibold">Filters</h4>

            <div className="mb-5">
              <p className="mb-1.5 text-[11px] font-medium text-muted-foreground">
                Embedding provider
              </p>
              {providers.length === 0 ? (
                <p className="text-[11px] text-muted-foreground">No KBs yet</p>
              ) : (
                <div className="space-y-1">
                  {providers.map((p) => (
                    <label
                      key={p}
                      className="flex cursor-pointer items-center gap-2 rounded-md px-1.5 py-1 text-xs transition-colors hover:bg-accent/50"
                    >
                      <input
                        type="checkbox"
                        checked={!excludedProviders.has(p)}
                        onChange={() => toggleProvider(p)}
                        className="h-3.5 w-3.5 rounded border-border"
                      />
                      <span className="font-mono">{p}</span>
                    </label>
                  ))}
                </div>
              )}
            </div>

            <div>
              <p className="mb-1.5 text-[11px] font-medium text-muted-foreground">
                Documents
              </p>
              <div className="space-y-1">
                {(
                  [
                    ["any", "Any"],
                    ["has", "Has documents"],
                    ["empty", "Empty"],
                  ] as const
                ).map(([val, label]) => (
                  <label
                    key={val}
                    className="flex cursor-pointer items-center gap-2 rounded-md px-1.5 py-1 text-xs transition-colors hover:bg-accent/50"
                  >
                    <input
                      type="radio"
                      name="filter-docs"
                      checked={filterDocs === val}
                      onChange={() => setFilterDocs(val)}
                      className="h-3.5 w-3.5 border-border"
                    />
                    <span>{label}</span>
                  </label>
                ))}
              </div>
            </div>
          </div>

          {/* ── Middle: search + list + create ────────────── */}
          <div className="flex min-h-0 flex-col border-r border-border">
            <div className="border-b border-border px-4 py-2.5">
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

            <div className="flex-1 overflow-y-auto p-2">
              {isLoading ? (
                <div className="flex h-40 items-center justify-center text-muted-foreground">
                  <Loader2 className="h-5 w-5 animate-spin" />
                </div>
              ) : filtered.length === 0 ? (
                <div className="flex h-40 flex-col items-center justify-center text-center">
                  <BookOpen className="mb-2 h-6 w-6 text-muted-foreground/40" />
                  <p className="text-xs text-muted-foreground">
                    {kbs.length === 0
                      ? "Chưa có knowledge nào"
                      : "Không khớp filter"}
                  </p>
                </div>
              ) : (
                <div className="flex flex-col gap-1">
                  {filtered.map((kb) => (
                    <KBRow
                      key={kb.id}
                      kb={kb}
                      attached={attachedIds.has(kb.id)}
                      selected={selectedIds.has(kb.id)}
                      highlighted={highlightId === kb.id}
                      onClick={() => setHighlightId(kb.id)}
                      onCheck={() => toggleSelect(kb.id)}
                    />
                  ))}
                </div>
              )}
            </div>

            <div className="border-t border-border p-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setCreateOpen(true)}
                className="w-full gap-1.5 text-xs"
              >
                <Plus className="h-3.5 w-3.5" />
                Create new knowledge
              </Button>
            </div>
          </div>

          {/* ── Right: detail ────────────────────────────── */}
          <div className="flex min-h-0 flex-col">
            {highlighted ? (
              <DetailPanel kb={highlighted} />
            ) : (
              <div className="flex h-full items-center justify-center p-6 text-center">
                <p className="text-xs text-muted-foreground">
                  Chọn một knowledge để xem chi tiết.
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-2 border-t border-border bg-muted/30 px-5 py-3">
          <Button variant="ghost" size="sm" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            size="sm"
            disabled={selectedIds.size === 0 || attach.isPending}
            onClick={handleAttach}
          >
            {attach.isPending ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              `Attach (${selectedIds.size})`
            )}
          </Button>
        </div>
      </DialogContent>

      {createOpen && (
        <QuickCreateKBDialog
          open={createOpen}
          onOpenChange={setCreateOpen}
          onCreated={handleCreated}
        />
      )}
    </>
  );
}

/* ─── KB row ──────────────────────────────────────────────── */

interface KBRowProps {
  kb: KnowledgeBase;
  attached: boolean;
  selected: boolean;
  highlighted: boolean;
  onClick: () => void;
  onCheck: () => void;
}

function KBRow({
  kb,
  attached,
  selected,
  highlighted,
  onClick,
  onCheck,
}: KBRowProps) {
  return (
    <div
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === "Enter" && onClick()}
      className={cn(
        "flex cursor-pointer items-center gap-3 rounded-lg border px-3 py-2.5 transition-colors",
        highlighted && "border-primary/40 bg-primary/5",
        !highlighted && "border-transparent hover:border-border hover:bg-accent/40",
        attached && "opacity-60",
      )}
    >
      <input
        type="checkbox"
        checked={selected}
        disabled={attached}
        onChange={onCheck}
        onClick={(e) => e.stopPropagation()}
        className="h-3.5 w-3.5 shrink-0 rounded border-border"
      />
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
          <span className="truncate font-mono">
            {kb.embedding_provider}/{kb.embedding_model}
          </span>
        </div>
      </div>
      {selected && <Check className="h-4 w-4 shrink-0 text-primary" />}
    </div>
  );
}

/* ─── Detail panel ────────────────────────────────────────── */

function DetailPanel({ kb }: { kb: KnowledgeBase }) {
  const { data: docs = [], isLoading } = useKBDocuments(kb.id);
  const upload = useUploadDocument(kb.id);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handlePick = () => fileInputRef.current?.click();
  const handleFiles = (files: FileList | null) => {
    if (!files) return;
    Array.from(files).forEach((f) => upload.mutate(f));
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  return (
    <div className="scrollbar-thin flex-1 overflow-y-auto p-4">
      <div className="flex items-start gap-2">
        <div className="flex h-8 w-8 items-center justify-center rounded-md border border-primary/25 bg-primary/10">
          <BookOpen className="h-4 w-4 text-primary" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold">{kb.name}</p>
          <p className="text-[11px] text-muted-foreground">
            {kb.description || "No description"}
          </p>
        </div>
      </div>

      <Separator className="my-3" />

      <dl className="space-y-1.5 text-[11px]">
        <SpecRow label="Documents" value={kb.total_documents} />
        <SpecRow label="Chunks" value={kb.total_chunks} />
        <SpecRow
          label="Embedding"
          value={
            <span className="font-mono">
              {kb.embedding_provider}/{kb.embedding_model}
            </span>
          }
        />
      </dl>

      <Separator className="my-3" />

      <div className="mb-2 flex items-center justify-between">
        <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
          Documents
        </p>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={handlePick}
          disabled={upload.isPending}
          className="h-7 gap-1.5 text-[11px]"
        >
          {upload.isPending ? (
            <Loader2 className="h-3 w-3 animate-spin" />
          ) : (
            <UploadCloud className="h-3 w-3" />
          )}
          Upload
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

      {isLoading ? (
        <div className="flex h-20 items-center justify-center text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
        </div>
      ) : docs.length === 0 ? (
        <p className="rounded-md border border-dashed border-border bg-muted/30 p-3 text-center text-[11px] text-muted-foreground">
          Chưa có document. Click Upload để thêm file.
        </p>
      ) : (
        <div className="space-y-1">
          {docs.map((doc) => (
            <DocRow key={doc.id} doc={doc} />
          ))}
        </div>
      )}
    </div>
  );
}

function DocRow({ doc }: { doc: KBDocument }) {
  return (
    <div className="flex items-center gap-2 rounded-md border border-border/60 bg-background/40 px-2.5 py-1.5 text-[11px]">
      <FileText className="h-3 w-3 shrink-0 text-muted-foreground" />
      <span className="min-w-0 flex-1 truncate">{doc.filename}</span>
      <DocStatus doc={doc} />
    </div>
  );
}

function DocStatus({ doc }: { doc: KBDocument }) {
  const { status, processing_phase, processing_progress } = doc;

  if (status === "ready") {
    return <CheckCircle2 className="h-3 w-3 text-emerald-500" />;
  }
  if (status === "failed") {
    return (
      <span
        title={doc.error_message ?? ""}
        className={cn(doc.error_message && "cursor-help")}
      >
        <AlertCircle className="h-3 w-3 text-destructive" />
      </span>
    );
  }
  const label = processing_phase
    ? processing_phase.charAt(0).toUpperCase() + processing_phase.slice(1)
    : "Pending";
  return (
    <span className="inline-flex items-center gap-1 text-[10px] text-amber-600 dark:text-amber-400">
      <Loader2 className="h-3 w-3 animate-spin" />
      {label}
      {typeof processing_progress === "number" && processing_phase === "embedding" && (
        <span className="font-mono">{processing_progress}%</span>
      )}
    </span>
  );
}

function SpecRow({
  label,
  value,
}: {
  label: string;
  value: React.ReactNode;
}) {
  return (
    <div className="flex items-center justify-between">
      <dt className="text-muted-foreground">{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}
