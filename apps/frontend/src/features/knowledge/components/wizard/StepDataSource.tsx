"use client";

import { useCallback, useState } from "react";
import { FileText, UploadCloud, Globe, Lock } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { WizardState } from "../../views/KnowledgeCreateWizard";

const ACCEPT = ".pdf,.txt,.md,.docx,.csv,.html";
const SUPPORTED = "PDF, TXT, MD, DOCX, CSV, HTML";
const MAX_MB = 15;

interface StepDataSourceProps {
  state: WizardState;
  update: (patch: Partial<WizardState>) => void;
  onNext: () => void;
  canNext: boolean;
}

export function StepDataSource({ state, update, onNext, canNext }: StepDataSourceProps) {
  const [drag, setDrag] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFile = useCallback(
    (file: File) => {
      setError(null);
      if (file.size > MAX_MB * 1024 * 1024) {
        setError(`File lớn hơn ${MAX_MB} MB. Vui lòng chọn file nhỏ hơn.`);
        return;
      }
      update({ file, createEmpty: false });
    },
    [update],
  );

  return (
    <div className="space-y-7">
      {/* Data source picker */}
      <section>
        <h2 className="mb-3 text-sm font-semibold">Data Source</h2>
        <div className="grid grid-cols-3 gap-3">
          <SourceCard active icon={FileText} label="Import from file" />
          <SourceCard disabled icon={NotionIcon} label="Sync from Notion" />
          <SourceCard disabled icon={Globe} label="Sync from website" />
        </div>
      </section>

      {/* Upload */}
      <section>
        <h3 className="mb-2 text-sm font-semibold">Upload file</h3>
        <div
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
          role="button"
          tabIndex={0}
          onClick={() => {
            const input = document.createElement("input");
            input.type = "file";
            input.accept = ACCEPT;
            input.onchange = (e) => {
              const f = (e.target as HTMLInputElement).files?.[0];
              if (f) handleFile(f);
            };
            input.click();
          }}
          className={cn(
            "flex cursor-pointer flex-col items-center justify-center gap-1.5 rounded-xl border-2 border-dashed px-6 py-10 transition-colors",
            drag
              ? "border-primary/60 bg-primary/5"
              : "border-border bg-muted/30 hover:border-primary/40 hover:bg-muted/50",
          )}
        >
          <UploadCloud
            className={cn("h-5 w-5", drag ? "text-primary" : "text-muted-foreground")}
          />
          <p className="text-xs">
            {state.file ? (
              <span className="font-medium text-foreground">{state.file.name}</span>
            ) : (
              <>
                Drag and drop file, or{" "}
                <span className="font-medium text-primary">Browse</span>
              </>
            )}
          </p>
          <p className="text-[10px] text-muted-foreground">
            Supports {SUPPORTED}. Max {MAX_MB} MB each. Max 1 file.
          </p>
        </div>

        {error && <p className="mt-2 text-xs text-destructive">{error}</p>}
      </section>

      {/* Actions */}
      <div className="flex items-center justify-between border-t border-border pt-4">
        <button
          type="button"
          onClick={() => {
            update({ file: null, createEmpty: true });
            onNext();
          }}
          className="flex items-center gap-1.5 text-xs text-primary hover:underline"
        >
          📁 I want to create an empty Knowledge
        </button>
        <Button size="sm" disabled={!canNext} onClick={onNext}>
          Next →
        </Button>
      </div>
    </div>
  );
}

function SourceCard({
  icon: Icon,
  label,
  active,
  disabled,
}: {
  icon: React.ElementType;
  label: string;
  active?: boolean;
  disabled?: boolean;
}) {
  return (
    <div
      className={cn(
        "flex items-center gap-2.5 rounded-xl border bg-card px-4 py-3 transition-colors",
        active && "border-primary bg-primary/5 shadow-sm",
        !active && !disabled && "border-border hover:border-primary/40",
        disabled && "border-border/60 bg-muted/30 opacity-60",
      )}
    >
      <div
        className={cn(
          "flex h-7 w-7 items-center justify-center rounded-md",
          active ? "bg-primary/10 text-primary" : "bg-muted text-muted-foreground",
        )}
      >
        <Icon className="h-3.5 w-3.5" />
      </div>
      <span className="flex-1 text-xs font-medium">{label}</span>
      {disabled && <Lock className="h-3 w-3 text-muted-foreground/60" />}
    </div>
  );
}

function NotionIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className={className}>
      <path d="M4.459 4.208c.746.606 1.026.56 2.428.466l13.215-.793c.28 0 .047-.28-.046-.326L17.86 1.968c-.42-.326-.981-.7-2.055-.607L3.01 2.295c-.466.046-.56.28-.374.466zm.793 3.08v13.904c0 .747.373 1.027 1.214.98l14.523-.84c.841-.046.935-.56.935-1.167V6.354c0-.606-.233-.933-.748-.887l-15.177.887c-.56.047-.747.327-.747.933zm14.337.745c.093.42 0 .84-.42.888l-.7.14v10.264c-.608.327-1.168.514-1.635.514-.748 0-.935-.234-1.495-.933l-4.577-7.186v6.952L12.21 19s0 .84-1.168.84l-3.222.186c-.093-.186 0-.653.327-.746l.84-.233V9.854L7.822 9.76c-.094-.42.14-1.026.793-1.073l3.456-.233 4.764 7.279v-6.44l-1.215-.139c-.093-.514.28-.887.747-.933z" />
    </svg>
  );
}
