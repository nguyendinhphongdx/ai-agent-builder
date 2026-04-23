"use client";

import { useEffect, useRef, useState } from "react";
import { CheckCircle2, Loader2, XCircle, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { knowledgeService } from "../../services/knowledgeService";
import type { WizardState } from "../../views/KnowledgeCreateWizard";

type Phase = "creating" | "uploading" | "processing" | "done" | "failed";

interface StepExecuteProps {
  state: WizardState;
  update: (patch: Partial<WizardState>) => void;
  onBack: () => void;
  onDone: (kbId: string) => void;
}

interface TaskStatus {
  label: string;
  status: "pending" | "running" | "done" | "failed";
  detail?: string;
}

export function StepExecute({ state, update, onBack, onDone }: StepExecuteProps) {
  const [phase, setPhase] = useState<Phase>("creating");
  const [tasks, setTasks] = useState<TaskStatus[]>([
    { label: "Tạo knowledge base", status: "pending" },
    { label: state.file ? `Upload "${state.file.name}"` : "Skip upload (empty knowledge)", status: "pending" },
    { label: "Parse & chunk document", status: "pending" },
    { label: "Generate embeddings", status: "pending" },
  ]);
  const [kbId, setKbId] = useState<string | null>(state.createdKbId);
  const [error, setError] = useState<string | null>(null);
  const started = useRef(false);

  const setTask = (idx: number, patch: Partial<TaskStatus>) =>
    setTasks((prev) => prev.map((t, i) => (i === idx ? { ...t, ...patch } : t)));

  useEffect(() => {
    if (started.current) return;
    started.current = true;

    (async () => {
      try {
        // 1. Create KB
        setPhase("creating");
        setTask(0, { status: "running" });
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
        setTask(0, { status: "done" });

        // 2. Upload document (if any)
        if (!state.file) {
          setTask(1, { status: "done", detail: "Empty knowledge — skipped" });
          setTask(2, { status: "done", detail: "Skipped" });
          setTask(3, { status: "done", detail: "Skipped" });
          setPhase("done");
          return;
        }

        setPhase("uploading");
        setTask(1, { status: "running" });
        setTask(2, { status: "running" });
        setTask(3, { status: "running" });

        const doc = await knowledgeService.uploadDocument(kb.id, state.file);

        if (doc.status === "ready") {
          setTask(1, { status: "done" });
          setTask(2, { status: "done", detail: `${doc.chunk_count} chunks` });
          setTask(3, { status: "done" });
          setPhase("done");
        } else if (doc.status === "failed") {
          setTask(1, { status: "done" });
          setTask(2, { status: "failed", detail: doc.error_message ?? "Processing failed" });
          setTask(3, { status: "failed" });
          setError(doc.error_message ?? "Processing failed");
          setPhase("failed");
        } else {
          // processing — keep running state for user to navigate anyway
          setTask(1, { status: "done" });
          setTask(2, { status: "running" });
          setPhase("processing");
        }
      } catch (e) {
        const msg =
          e instanceof Error ? e.message : "Unknown error while creating knowledge";
        setError(msg);
        setTasks((prev) =>
          prev.map((t) =>
            t.status === "running" || t.status === "pending"
              ? { ...t, status: "failed" }
              : t,
          ),
        );
        setPhase("failed");
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const finished = phase === "done" || phase === "processing";

  return (
    <div className="space-y-6">
      <section>
        <h2 className="mb-1 text-sm font-semibold">Execute & Finish</h2>
        <p className="text-xs text-muted-foreground">
          Knowledge đang được tạo và xử lý. Bạn có thể xem tiến trình hoặc chuyển tới trang
          detail sau khi xong.
        </p>
      </section>

      <div className="space-y-2 rounded-xl border border-border bg-card/80 p-5">
        {tasks.map((task, i) => (
          <TaskRow key={i} task={task} />
        ))}
      </div>

      {error && (
        <div className="rounded-md border border-destructive/30 bg-destructive/5 px-4 py-3 text-xs text-destructive">
          {error}
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center justify-between border-t border-border pt-4">
        <Button variant="ghost" size="sm" onClick={onBack} disabled={phase !== "failed"}>
          ← Back
        </Button>
        <Button
          size="sm"
          disabled={!finished || !kbId}
          onClick={() => kbId && onDone(kbId)}
          className="gap-1.5"
        >
          Go to Knowledge <ArrowRight className="h-3.5 w-3.5" />
        </Button>
      </div>
    </div>
  );
}

function TaskRow({ task }: { task: TaskStatus }) {
  return (
    <div className="flex items-center gap-2.5 py-1.5">
      <StatusIcon status={task.status} />
      <span
        className={cn(
          "flex-1 text-sm",
          task.status === "done" && "text-foreground",
          task.status === "failed" && "text-destructive",
          task.status === "pending" && "text-muted-foreground/70",
        )}
      >
        {task.label}
      </span>
      {task.detail && (
        <span className="text-[11px] text-muted-foreground">{task.detail}</span>
      )}
    </div>
  );
}

function StatusIcon({ status }: { status: TaskStatus["status"] }) {
  if (status === "running") return <Loader2 className="h-4 w-4 animate-spin text-primary" />;
  if (status === "done") return <CheckCircle2 className="h-4 w-4 text-emerald-500" />;
  if (status === "failed") return <XCircle className="h-4 w-4 text-destructive" />;
  return <div className="h-4 w-4 rounded-full border border-border" />;
}
