"use client";

import { useCallback, useState } from "react";
import { BookOpen, Loader2, UploadCloud, X } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { Textarea } from "@/components/ui/textarea";
import { useQueryClient } from "@tanstack/react-query";
import { cn } from "@/lib/utils";
import { useCreateKnowledgeBase, kbKeys } from "@/features/knowledge/hooks/useKnowledge";
import { knowledgeService } from "@/features/knowledge/services/knowledgeService";
import type { KnowledgeBase } from "@/features/knowledge/types";

const ACCEPT = ".pdf,.txt,.md,.docx,.csv,.html";
const MAX_MB = 15;

interface QuickCreateKBDialogProps {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  /** Called after create (+optional upload) succeeds. Parent should attach to agent. */
  onCreated: (kb: KnowledgeBase) => void;
}

export function QuickCreateKBDialog(props: QuickCreateKBDialogProps) {
  // Render body only when open → state resets via remount (no set-state-in-effect)
  return (
    <Dialog open={props.open} onOpenChange={props.onOpenChange}>
      {props.open && <Body {...props} />}
    </Dialog>
  );
}

function Body({ onOpenChange, onCreated }: QuickCreateKBDialogProps) {
  const queryClient = useQueryClient();
  const createKB = useCreateKnowledgeBase();

  const [file, setFile] = useState<File | null>(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [chunkSize, setChunkSize] = useState(1024);
  const [chunkOverlap, setChunkOverlap] = useState(100);
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [drag, setDrag] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const handleFile = useCallback((f: File) => {
    setError(null);
    if (f.size > MAX_MB * 1024 * 1024) {
      setError(`File lớn hơn ${MAX_MB} MB.`);
      return;
    }
    setFile(f);
    // Auto-fill name from filename if empty
    setName((prev) => prev || f.name.replace(/\.[^/.]+$/, ""));
  }, []);

  const pickFile = () => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ACCEPT;
    input.onchange = (e) => {
      const f = (e.target as HTMLInputElement).files?.[0];
      if (f) handleFile(f);
    };
    input.click();
  };

  const handleSubmit = async () => {
    const trimmed = name.trim();
    if (!trimmed) {
      setError("Name is required");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const kb = await createKB.mutateAsync({
        name: trimmed,
        description: description.trim() || undefined,
        chunk_size: chunkSize,
        chunk_overlap: chunkOverlap,
      });

      if (file) {
        // Fire-and-forget upload — backend runs ingestion async via dispatcher.
        // Don't await; KB list will pick up the new doc via socket events.
        knowledgeService.uploadDocument(kb.id, file).finally(() => {
          queryClient.invalidateQueries({ queryKey: kbKeys.documents(kb.id) });
          queryClient.invalidateQueries({ queryKey: kbKeys.detail(kb.id) });
        });
      }

      onCreated(kb);
      onOpenChange(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create knowledge");
      setSubmitting(false);
    }
  };

  return (
    <DialogContent className="sm:max-w-lg">
      <DialogHeader>
        <DialogTitle>Create new knowledge</DialogTitle>
        <DialogDescription className="text-xs">
          Tạo knowledge mới và (tuỳ chọn) upload 1 file đầu tiên. Sau đó tự động attach vào agent.
        </DialogDescription>
      </DialogHeader>

      <div className="space-y-3 py-1">
        {/* Name */}
        <div className="space-y-1.5">
          <Label htmlFor="qc-name" className="text-xs">
            Name <span className="text-destructive">*</span>
          </Label>
          <Input
            id="qc-name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Product docs"
            className="h-9 text-sm"
            autoFocus
          />
        </div>

        {/* Description */}
        <div className="space-y-1.5">
          <Label htmlFor="qc-desc" className="text-xs">
            Description (optional)
          </Label>
          <Textarea
            id="qc-desc"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={2}
            className="resize-none text-sm"
          />
        </div>

        {/* File drop */}
        <div className="space-y-1.5">
          <Label className="text-xs">File (optional)</Label>
          {file ? (
            <div className="flex items-center gap-2 rounded-md border border-border bg-muted/40 px-3 py-2">
              <BookOpen className="h-3.5 w-3.5 text-muted-foreground" />
              <span className="flex-1 truncate text-xs">{file.name}</span>
              <span className="text-[10px] text-muted-foreground">
                {(file.size / 1024 / 1024).toFixed(2)} MB
              </span>
              <button
                type="button"
                onClick={() => setFile(null)}
                className="text-muted-foreground hover:text-destructive"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
          ) : (
            <div
              role="button"
              tabIndex={0}
              onClick={pickFile}
              onKeyDown={(e) => e.key === "Enter" && pickFile()}
              onDragOver={(e) => {
                e.preventDefault();
                setDrag(true);
              }}
              onDragLeave={() => setDrag(false)}
              onDrop={(e) => {
                e.preventDefault();
                setDrag(false);
                const f = e.dataTransfer.files?.[0];
                if (f) handleFile(f);
              }}
              className={cn(
                "flex cursor-pointer flex-col items-center gap-1 rounded-md border-2 border-dashed px-4 py-4 transition-colors",
                drag
                  ? "border-primary/60 bg-primary/5"
                  : "border-border bg-muted/20 hover:border-primary/40 hover:bg-muted/40",
              )}
            >
              <UploadCloud
                className={cn(
                  "h-4 w-4",
                  drag ? "text-primary" : "text-muted-foreground",
                )}
              />
              <p className="text-[11px]">
                Drop file or{" "}
                <span className="font-medium text-primary">browse</span>
              </p>
              <p className="text-[10px] text-muted-foreground">
                PDF, TXT, MD, DOCX, CSV, HTML · max {MAX_MB} MB
              </p>
            </div>
          )}
        </div>

        {/* Advanced */}
        <div className="space-y-2">
          <button
            type="button"
            onClick={() => setAdvancedOpen((v) => !v)}
            className="text-[11px] font-medium text-muted-foreground hover:text-foreground"
          >
            {advancedOpen ? "▾" : "▸"} Advanced chunking
          </button>
          {advancedOpen && (
            <div className="space-y-3 rounded-md border border-border bg-muted/30 p-3">
              <SliderRow
                label="Chunk size"
                value={chunkSize}
                min={100}
                max={4000}
                step={50}
                unit="chars"
                onChange={setChunkSize}
              />
              <SliderRow
                label="Chunk overlap"
                value={chunkOverlap}
                min={0}
                max={Math.min(500, chunkSize - 1)}
                step={10}
                unit="chars"
                onChange={setChunkOverlap}
              />
            </div>
          )}
        </div>

        {error && <p className="text-xs text-destructive">{error}</p>}
      </div>

      <DialogFooter>
        <Button variant="ghost" size="sm" onClick={() => onOpenChange(false)}>
          Cancel
        </Button>
        <Button
          size="sm"
          disabled={!name.trim() || submitting}
          onClick={handleSubmit}
        >
          {submitting ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            "Create & Attach"
          )}
        </Button>
      </DialogFooter>
    </DialogContent>
  );
}

/* ─── Helpers ───────────────────────────────────────────────── */

function SliderRow({
  label,
  value,
  min,
  max,
  step,
  unit,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  unit?: string;
  onChange: (v: number) => void;
}) {
  return (
    <div>
      <div className="mb-1.5 flex items-center justify-between">
        <Label className="text-xs">{label}</Label>
        <span className="font-mono text-[11px] tabular-nums text-muted-foreground">
          {value}
          {unit ? ` ${unit}` : ""}
        </span>
      </div>
      <Slider
        min={min}
        max={max}
        step={step}
        value={[value]}
        onValueChange={(vals) => onChange(vals[0])}
      />
    </div>
  );
}

