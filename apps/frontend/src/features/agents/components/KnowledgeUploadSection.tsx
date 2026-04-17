"use client";

import { useState, useCallback, useEffect } from "react";
import {
  Upload,
  File,
  X,
  CheckCircle2,
  Loader2,
  AlertCircle,
} from "lucide-react";
import { useKnowledgeBasesByAgent } from "@/features/knowledge/hooks/useKnowledge";
import { knowledgeService } from "@/features/knowledge/services/knowledgeService";
import { cn } from "@/lib/utils";

interface TrackedFile {
  id: string;
  name: string;
  size: number;
  status: "uploading" | "processing" | "ready" | "failed";
  progress?: number;
  error?: string;
  chunkCount?: number;
}

interface KnowledgeUploadSectionProps {
  agentId?: string;
}

export function KnowledgeUploadSection({ agentId }: KnowledgeUploadSectionProps) {
  const [trackedFiles, setTrackedFiles] = useState<TrackedFile[]>([]);
  const [isDragOver, setIsDragOver] = useState(false);
  const [kbId, setKbId] = useState<string | null>(null);

  // Load existing KB attached to this agent
  const { data: agentKBs } = useKnowledgeBasesByAgent(agentId ?? "");
  useEffect(() => {
    if (agentKBs && agentKBs.length > 0) {
      setKbId(agentKBs[0].id);
    }
  }, [agentKBs]);

  const updateTracked = (id: string, updates: Partial<TrackedFile>) => {
    setTrackedFiles((prev) => prev.map((f) => (f.id === id ? { ...f, ...updates } : f)));
  };

  const ensureKB = useCallback(async (): Promise<string | null> => {
    if (kbId) return kbId;
    if (!agentId) return null;

    const created = await knowledgeService.create({ name: "Agent Knowledge Base" });
    await knowledgeService.attachToAgent(agentId, created.id);
    setKbId(created.id);
    return created.id;
  }, [agentId, kbId]);

  const handleUpload = useCallback(
    async (file: globalThis.File, trackId: string) => {
      const resolvedKbId = await ensureKB();
      if (!resolvedKbId) {
        updateTracked(trackId, { status: "failed", error: "Save agent first" });
        return;
      }

      updateTracked(trackId, { status: "uploading", progress: 50 });

      try {
        const doc = await knowledgeService.uploadDocument(resolvedKbId, file);
        if (doc.status === "ready") {
          updateTracked(trackId, { status: "ready", progress: 100, chunkCount: doc.chunk_count });
        } else if (doc.status === "failed") {
          updateTracked(trackId, { status: "failed", error: doc.error_message || "Failed" });
        } else {
          updateTracked(trackId, { status: "processing", progress: 80 });
        }
      } catch (err: any) {
        updateTracked(trackId, {
          status: "failed",
          error: err?.response?.data?.detail || "Upload failed",
        });
      }
    },
    [ensureKB]
  );

  const handleFiles = useCallback(
    (fileList: FileList) => {
      const newFiles: TrackedFile[] = Array.from(fileList).map((f) => ({
        id: crypto.randomUUID(),
        name: f.name,
        size: f.size,
        status: "uploading" as const,
        progress: 0,
      }));
      setTrackedFiles((prev) => [...prev, ...newFiles]);

      Array.from(fileList).forEach((file, i) => {
        handleUpload(file, newFiles[i].id);
      });
    },
    [handleUpload]
  );

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="space-y-3">
      {/* Drop zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
        onDragLeave={() => setIsDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setIsDragOver(false);
          if (e.dataTransfer.files.length > 0) handleFiles(e.dataTransfer.files);
        }}
        role="button"
        tabIndex={0}
        className={cn(
          "relative flex cursor-pointer flex-col items-center justify-center gap-1.5 rounded-xl border-2 border-dashed px-4 py-7 transition-colors",
          isDragOver
            ? "border-primary/60 bg-primary/5"
            : "border-border bg-muted/30 hover:border-primary/40 hover:bg-muted/50"
        )}
        onClick={() => {
          const input = document.createElement("input");
          input.type = "file";
          input.multiple = true;
          input.accept = ".pdf,.txt,.md,.docx,.csv,.html";
          input.onchange = (e) => {
            const t = e.target as HTMLInputElement;
            if (t.files) handleFiles(t.files);
          };
          input.click();
        }}
        onKeyDown={(e) => e.key === "Enter" && (e.currentTarget as HTMLElement).click()}
      >
        <div className={cn(
          "flex h-9 w-9 items-center justify-center rounded-full border transition-colors",
          isDragOver ? "border-primary/40 bg-primary/10" : "border-border bg-background"
        )}>
          <Upload className={cn("h-4 w-4", isDragOver ? "text-primary" : "text-muted-foreground")} />
        </div>
        <p className="text-xs text-muted-foreground">
          Drop files or <span className="font-medium text-primary">browse</span>
        </p>
        <p className="text-[10px] text-muted-foreground/60">PDF, TXT, MD, DOCX, CSV, HTML</p>
        {!agentId && (
          <p className="text-[10px] text-amber-600 dark:text-amber-400">Save agent first to enable uploads</p>
        )}
      </div>

      {/* File list */}
      {trackedFiles.length > 0 && (
        <div className="space-y-1.5">
          {trackedFiles.map((f) => (
            <div key={f.id} className="flex items-center gap-3 rounded-lg border border-border bg-background/60 px-3 py-2.5">
              <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md border border-border bg-muted/60">
                <File className="h-3.5 w-3.5 text-muted-foreground" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <p className="truncate text-xs font-medium">{f.name}</p>
                  <span className="shrink-0 text-[10px] text-muted-foreground/70">{formatSize(f.size)}</span>
                </div>
                {f.status === "uploading" && (
                  <div className="mt-1.5 h-1 w-full overflow-hidden rounded-full bg-muted">
                    <div className="h-full rounded-full bg-primary transition-all" style={{ width: `${f.progress ?? 0}%` }} />
                  </div>
                )}
                {f.status === "processing" && (
                  <p className="mt-0.5 flex items-center gap-1 text-[10px] text-amber-600 dark:text-amber-400">
                    <Loader2 className="h-2.5 w-2.5 animate-spin" />Processing...
                  </p>
                )}
                {f.status === "ready" && (
                  <p className="mt-0.5 text-[10px] text-emerald-600 dark:text-emerald-400">
                    Ready{f.chunkCount ? ` · ${f.chunkCount} chunks` : ""}
                  </p>
                )}
                {f.status === "failed" && f.error && (
                  <p className="mt-0.5 text-[10px] text-destructive">{f.error}</p>
                )}
              </div>
              <div className="shrink-0">
                {f.status === "ready" && <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />}
                {f.status === "failed" && <AlertCircle className="h-4 w-4 text-destructive" />}
                {(f.status === "uploading" || f.status === "processing") && <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />}
              </div>
              <button
                type="button"
                onClick={(e) => { e.stopPropagation(); setTrackedFiles((prev) => prev.filter((x) => x.id !== f.id)); }}
                className="shrink-0 rounded p-0.5 text-muted-foreground/40 hover:text-foreground"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
