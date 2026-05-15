"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowLeft, Check } from "lucide-react";
import { cn } from "@/lib/utils";
import { StepDataSource } from "../components/wizard/StepDataSource";
import { StepProcessing } from "../components/wizard/StepProcessing";
import { StepExecute } from "../components/wizard/StepExecute";

export interface WizardState {
  // Step 1
  file: File | null;
  createEmpty: boolean;

  // Step 2
  name: string;
  description: string;
  chunk_size: number;
  chunk_overlap: number;
  chunk_strategy: string;
  retrieval_top_k: number;
  retrieval_score_threshold: number;

  // Step 3 output
  createdKbId: string | null;
}

const STEPS = [
  { key: "source", label: "DATA SOURCE" },
  { key: "processing", label: "DOCUMENT PROCESSING" },
  { key: "execute", label: "EXECUTE & FINISH" },
] as const;

function deriveName(file: File | null): string {
  if (!file) return "Untitled Knowledge";
  return file.name.replace(/\.[^/.]+$/, "");
}

export function KnowledgeCreateWizard() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [state, setState] = useState<WizardState>({
    file: null,
    createEmpty: false,
    name: "",
    description: "",
    chunk_size: 1024,
    chunk_overlap: 100,
    chunk_strategy: "recursive",
    retrieval_top_k: 5,
    retrieval_score_threshold: 0.5,
    createdKbId: null,
  });

  const update = (patch: Partial<WizardState>) => setState((s) => ({ ...s, ...patch }));

  const goNext = () => {
    if (step === 0 && !state.name) update({ name: deriveName(state.file) });
    setStep((s) => Math.min(s + 1, STEPS.length - 1));
  };
  const goBack = () => setStep((s) => Math.max(s - 1, 0));

  const canNext =
    step === 0
      ? state.createEmpty || !!state.file
      : step === 1
      ? !!state.name.trim() && state.chunk_size > 0
      : false;

  return (
    <div className="flex h-full flex-col bg-background">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-6 py-3.5">
        <Link
          href={"/ws/knowledge"}
          className="flex items-center gap-1.5 text-xs font-semibold tracking-wider text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          KNOWLEDGE
        </Link>

        {/* Step indicator */}
        <div className="flex items-center gap-2">
          {STEPS.map((s, i) => {
            const done = i < step;
            const active = i === step;
            return (
              <div key={s.key} className="flex items-center gap-2">
                <div
                  className={cn(
                    "flex items-center gap-2 rounded-full px-3 py-1 text-[11px] font-semibold tracking-wider transition-colors",
                    active && "bg-primary text-primary-foreground",
                    done && "text-primary",
                    !active && !done && "text-muted-foreground",
                  )}
                >
                  <span
                    className={cn(
                      "flex h-4 w-4 items-center justify-center rounded-full text-[10px]",
                      active
                        ? "bg-primary-foreground/25 text-primary-foreground"
                        : done
                        ? "bg-primary text-primary-foreground"
                        : "bg-muted text-muted-foreground",
                    )}
                  >
                    {done ? <Check className="h-2.5 w-2.5" /> : <span>{i + 1}</span>}
                  </span>
                  <span>{s.label}</span>
                </div>
                {i < STEPS.length - 1 && (
                  <div className="h-px w-6 bg-border" />
                )}
              </div>
            );
          })}
        </div>

        <div className="w-16" />
      </div>

      {/* Body */}
      <div className="scrollbar-thin flex-1 overflow-auto">
        <div className="mx-auto w-full max-w-4xl p-8">
          {step === 0 && (
            <StepDataSource
              state={state}
              update={update}
              onNext={goNext}
              canNext={canNext}
            />
          )}
          {step === 1 && (
            <StepProcessing
              state={state}
              update={update}
              onBack={goBack}
              onNext={goNext}
              canNext={canNext}
            />
          )}
          {step === 2 && (
            <StepExecute
              state={state}
              update={update}
              onBack={goBack}
              onDone={(kbId) => router.push(`/ws/knowledge/${kbId}`)}
            />
          )}
        </div>
      </div>
    </div>
  );
}
