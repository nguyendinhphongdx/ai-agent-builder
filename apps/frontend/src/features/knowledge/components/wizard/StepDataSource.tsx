"use client";

import { useCallback, useState } from "react";
import { UploadCloud } from "lucide-react";
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
      {/* Upload */}
      <section>
        <h2 className="mb-2 text-sm font-semibold">Upload file</h2>
        <p className="mb-3 text-[11px] text-muted-foreground">
          Other sources (Slack / Notion / Drive / S3 / web crawler / …) wire
          in from the <span className="font-medium">Connectors</span> tab on
          the KB detail page after this wizard finishes.
        </p>
      </section>
      <section>
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

