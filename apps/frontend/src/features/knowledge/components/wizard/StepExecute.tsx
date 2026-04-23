"use client";

import { useEffect, useRef, useState } from "react";
import { CheckCircle2, Loader2, XCircle, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useSocketEvent } from "@/features/notifications/hooks/useSocketEvent";
import { knowledgeService } from "../../services/knowledgeService";
import type {
  DocumentPhase,
  DocumentProgressEvent,
} from "../../types";
import type { WizardState } from "../../views/KnowledgeCreateWizard";

interface StepExecuteProps {
  state: WizardState;
  update: (patch: Partial<WizardState>) => void;
  onBack: () => void;
  onDone: (kbId: string) => void;
}

type RowStatus = "pending" | "running" | "done" | "failed";

interface Row {
  key: string;
  label: string;
  status: RowStatus;
  detail?: string;
  progress?: number;
}

const INGESTION_PHASES: { key: DocumentPhase; label: string }[] = [
  { key: "parsing", label: "Parse document" },
  { key: "chunking", label: "Split into chunks" },
  { key: "embedding", label: "Generate embeddings" },
];

export function StepExecute({ state, update, onBack, onDone }: StepExecuteProps) {
  // ── Top-level rows (KB + upload + per-phase ingestion rows) ────────────
  const [kbRow, setKbRow] = useState<Row>({
    key: "kb",
    label: "Tạo knowledge base",
    status: "pending",
  });
  const [uploadRow, setUploadRow] = useState<Row>({
    key: "upload",
    label: state.file ? `Upload "${state.file.name}"` : "Skip upload (empty knowledge)",
    status: "pending",
  });
  const [phaseRows, setPhaseRows] = useState<Row[]>(
    INGESTION_PHASES.map((p) => ({ key: p.key as string, label: p.label, status: "pending" })),
  );

  const [kbId, setKbId] = useState<string | null>(state.createdKbId);
  const [docId, setDocId] = useState<string | null>(null);
  const [finished, setFinished] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const started = useRef(false);

  const markPhase = (phase: DocumentPhase, patch: Partial<Row>) =>
    setPhaseRows((rows) =>
      rows.map((r) => (r.key === phase ? { ...r, ...patch } : r)),
    );

  // ── Socket listener: reflect real ingestion phases ───────────────────
  useSocketEvent<DocumentProgressEvent>("document:progress", (p) => {
    if (!docId || p.doc_id !== docId) return;

    // Mark prior phases as done when current one advances
    const phaseOrder: DocumentPhase[] = ["parsing", "chunking", "embedding"];
    const currentIdx = p.phase ? phaseOrder.indexOf(p.phase) : -1;

    setPhaseRows((rows) =>
      rows.map((row, idx) => {
        const rowIdx = phaseOrder.indexOf(row.key as DocumentPhase);
        if (p.status === "failed") {
          if (idx <= currentIdx || rowIdx === currentIdx) {
            return { ...row, status: row.status === "running" ? "failed" : row.status };
          }
          return row;
        }
        if (p.status === "ready") {
          return { ...row, status: "done" };
        }
        // processing: phases before current are done, current is running, later are pending
        if (rowIdx < currentIdx) return { ...row, status: "done" };
        if (rowIdx === currentIdx) {
          return {
            ...row,
            status: "running",
            progress: row.key === "embedding" ? p.progress ?? undefined : undefined,
          };
        }
        return { ...row, status: "pending" };
      }),
    );

    if (p.status === "ready") {
      markPhase("embedding", { status: "done", detail: `${p.chunk_count} chunks` });
      setFinished(true);
    } else if (p.status === "failed") {
      setError(p.error_message ?? "Ingestion failed");
      setFinished(true);
    }
  });

  // ── Kick off: create KB + upload ─────────────────────────────────────
  useEffect(() => {
    if (started.current) return;
    started.current = true;

    (async () => {
      try {
        setKbRow((r) => ({ ...r, status: "running" }));
        const kb = await knowledgeService.create({
          name: state.name,
          description: state.description || undefined,
          chunk_size: state.chunk_size,
          chunk_overlap: state.chunk_overlap,
          chunk_strategy: state.chunk_strategy,
          retrieval_top_k: state.retrieval_top_k,
          retrieval_score_threshold: state.retrieval_score_threshold,
        });
        setKbId(kb.id);
        update({ createdKbId: kb.id });
        setKbRow((r) => ({ ...r, status: "done" }));

        if (!state.file) {
          setUploadRow((r) => ({ ...r, status: "done", detail: "Skipped" }));
          setPhaseRows((rows) =>
            rows.map((r) => ({ ...r, status: "done", detail: "Skipped" })),
          );
          setFinished(true);
          return;
        }

        setUploadRow((r) => ({ ...r, status: "running" }));
        const doc = await knowledgeService.uploadDocument(kb.id, state.file);
        setDocId(doc.id);
        setUploadRow((r) => ({ ...r, status: "done" }));

        // Ingestion runs server-side; progress comes in via socket.
        // Handle edge case where it finished before socket wired up:
        if (doc.status === "ready") {
          setPhaseRows((rows) => rows.map((r) => ({ ...r, status: "done" })));
          setFinished(true);
        } else if (doc.status === "failed") {
          setError(doc.error_message ?? "Processing failed");
          setPhaseRows((rows) =>
            rows.map((r) =>
              r.status === "pending" ? { ...r, status: "failed" } : r,
            ),
          );
          setFinished(true);
        }
      } catch (e) {
        const msg = e instanceof Error ? e.message : "Unknown error";
        setError(msg);
        setKbRow((r) => (r.status === "running" ? { ...r, status: "failed" } : r));
        setUploadRow((r) => (r.status === "running" ? { ...r, status: "failed" } : r));
        setFinished(true);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const allRows: Row[] = [kbRow, uploadRow, ...phaseRows];

  return (
    <div className="space-y-6">
      <section>
        <h2 className="mb-1 text-sm font-semibold">Execute & Finish</h2>
        <p className="text-xs text-muted-foreground">
          Knowledge đang được tạo. Ingestion chạy nền — progress dưới đây cập nhật realtime
          qua socket. Bạn có thể đợi xong hoặc chuyển sang trang detail ngay.
        </p>
      </section>

      <div className="space-y-1 rounded-xl border border-border bg-card/80 p-5">
        {allRows.map((row) => (
          <TaskRow key={row.key} row={row} />
        ))}
      </div>

      {error && (
        <div className="rounded-md border border-destructive/30 bg-destructive/5 px-4 py-3 text-xs text-destructive">
          {error}
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center justify-between border-t border-border pt-4">
        <Button variant="ghost" size="sm" onClick={onBack} disabled={!finished || !error}>
          ← Back
        </Button>
        <Button
          size="sm"
          disabled={!kbId}
          onClick={() => kbId && onDone(kbId)}
          className="gap-1.5"
        >
          {finished ? "Go to Knowledge" : "Open now"}
          <ArrowRight className="h-3.5 w-3.5" />
        </Button>
      </div>
    </div>
  );
}

function TaskRow({ row }: { row: Row }) {
  const showProgress = row.status === "running" && typeof row.progress === "number";

  return (
    <div className="py-1.5">
      <div className="flex items-center gap-2.5">
        <StatusIcon status={row.status} />
        <span
          className={cn(
            "flex-1 text-sm",
            row.status === "done" && "text-foreground",
            row.status === "failed" && "text-destructive",
            row.status === "pending" && "text-muted-foreground/70",
          )}
        >
          {row.label}
        </span>
        {showProgress && (
          <span className="font-mono text-[10px] tabular-nums text-muted-foreground">
            {row.progress}%
          </span>
        )}
        {row.detail && !showProgress && (
          <span className="text-[11px] text-muted-foreground">{row.detail}</span>
        )}
      </div>
      {showProgress && (
        <div className="ml-6 mt-1.5 h-1 w-full overflow-hidden rounded-full bg-muted">
          <div
            className="h-full rounded-full bg-primary transition-all duration-300"
            style={{ width: `${row.progress}%` }}
          />
        </div>
      )}
    </div>
  );
}

function StatusIcon({ status }: { status: RowStatus }) {
  if (status === "running") return <Loader2 className="h-4 w-4 animate-spin text-primary" />;
  if (status === "done") return <CheckCircle2 className="h-4 w-4 text-emerald-500" />;
  if (status === "failed") return <XCircle className="h-4 w-4 text-destructive" />;
  return <div className="h-4 w-4 rounded-full border border-border" />;
}
