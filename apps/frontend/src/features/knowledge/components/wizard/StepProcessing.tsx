"use client";

import { Settings2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { Textarea } from "@/components/ui/textarea";
import type { WizardState } from "../../views/KnowledgeCreateWizard";

interface StepProcessingProps {
  state: WizardState;
  update: (patch: Partial<WizardState>) => void;
  onBack: () => void;
  onNext: () => void;
  canNext: boolean;
}

export function StepProcessing({ state, update, onBack, onNext, canNext }: StepProcessingProps) {
  return (
    <div className="space-y-7">
      <section>
        <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold">
          <Settings2 className="h-4 w-4 text-primary" />
          Document Processing
        </h2>

        {/* Name + description */}
        <div className="space-y-4 rounded-xl border border-border bg-card/80 p-5">
          <div className="space-y-1.5">
            <Label htmlFor="kb-name" className="text-xs">
              Knowledge name <span className="text-destructive">*</span>
            </Label>
            <Input
              id="kb-name"
              value={state.name}
              onChange={(e) => update({ name: e.target.value })}
              placeholder="Ví dụ: Product documentation"
              className="h-9 text-sm"
              autoFocus
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="kb-desc" className="text-xs">
              Description (optional)
            </Label>
            <Textarea
              id="kb-desc"
              value={state.description}
              onChange={(e) => update({ description: e.target.value })}
              placeholder="Mô tả nội dung của knowledge — giúp agent biết nên retrieve khi nào."
              rows={2}
              className="resize-none text-sm"
            />
          </div>
        </div>
      </section>

      {/* Chunking */}
      <section>
        <h3 className="mb-2 text-sm font-semibold">Chunk Settings</h3>
        <div className="space-y-5 rounded-xl border border-border bg-card/80 p-5">
          <NumberSlider
            label="Chunk size"
            hint="Số ký tự mỗi chunk. Lớn = ngữ cảnh rộng, nhỏ = độ khớp cao."
            value={state.chunk_size}
            onChange={(v) => update({ chunk_size: v })}
            min={100}
            max={4000}
            step={50}
            unit="chars"
          />
          <NumberSlider
            label="Chunk overlap"
            hint="Số ký tự trùng giữa 2 chunk liên tiếp — giữ mạch ngữ nghĩa."
            value={state.chunk_overlap}
            onChange={(v) => update({ chunk_overlap: v })}
            min={0}
            max={Math.min(500, state.chunk_size - 1)}
            step={10}
            unit="chars"
          />
        </div>
      </section>

      {/* Retrieval */}
      <section>
        <h3 className="mb-2 text-sm font-semibold">Retrieval Settings</h3>
        <div className="space-y-5 rounded-xl border border-border bg-card/80 p-5">
          <NumberSlider
            label="Top K"
            hint="Số chunk tối đa trả về khi agent query."
            value={state.retrieval_top_k}
            onChange={(v) => update({ retrieval_top_k: v })}
            min={1}
            max={20}
            step={1}
          />
          <NumberSlider
            label="Score threshold"
            hint="Chunk phải đạt điểm cosine tối thiểu này mới được trả về."
            value={state.retrieval_score_threshold}
            onChange={(v) => update({ retrieval_score_threshold: v })}
            min={0}
            max={1}
            step={0.05}
            fixed={2}
          />
        </div>
      </section>

      {/* Actions */}
      <div className="flex items-center justify-between border-t border-border pt-4">
        <Button variant="ghost" size="sm" onClick={onBack}>
          ← Back
        </Button>
        <Button size="sm" disabled={!canNext} onClick={onNext}>
          Save & Process →
        </Button>
      </div>
    </div>
  );
}

function NumberSlider({
  label,
  hint,
  value,
  onChange,
  min,
  max,
  step,
  unit,
  fixed = 0,
}: {
  label: string;
  hint?: string;
  value: number;
  onChange: (v: number) => void;
  min: number;
  max: number;
  step: number;
  unit?: string;
  fixed?: number;
}) {
  return (
    <div>
      <div className="mb-1.5 flex items-center justify-between">
        <Label className="text-xs">{label}</Label>
        <span className="font-mono text-[11px] tabular-nums text-muted-foreground">
          {fixed > 0 ? value.toFixed(fixed) : value}
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
      {hint && <p className="mt-1.5 text-[10px] text-muted-foreground">{hint}</p>}
    </div>
  );
}
