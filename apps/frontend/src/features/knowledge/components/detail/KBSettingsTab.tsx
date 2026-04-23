"use client";

import { useEffect, useState } from "react";
import { Save, Loader2, Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import {
  useUpdateKnowledgeBase,
  useDeleteKnowledgeBase,
} from "../../hooks/useKnowledge";
import type { KnowledgeBase } from "../../types";

interface KBSettingsTabProps {
  kb: KnowledgeBase;
}

export function KBSettingsTab({ kb }: KBSettingsTabProps) {
  const router = useRouter();
  const update = useUpdateKnowledgeBase(kb.id);
  const destroy = useDeleteKnowledgeBase();

  const [name, setName] = useState(kb.name);
  const [description, setDescription] = useState(kb.description ?? "");
  const [chunkSize, setChunkSize] = useState(kb.chunk_size);
  const [chunkOverlap, setChunkOverlap] = useState(kb.chunk_overlap);
  const [topK, setTopK] = useState(kb.retrieval_top_k);
  const [threshold, setThreshold] = useState(kb.retrieval_score_threshold);
  const [confirmDelete, setConfirmDelete] = useState(false);

  useEffect(() => {
    setName(kb.name);
    setDescription(kb.description ?? "");
    setChunkSize(kb.chunk_size);
    setChunkOverlap(kb.chunk_overlap);
    setTopK(kb.retrieval_top_k);
    setThreshold(kb.retrieval_score_threshold);
  }, [kb]);

  const dirty =
    name !== kb.name ||
    description !== (kb.description ?? "") ||
    chunkSize !== kb.chunk_size ||
    chunkOverlap !== kb.chunk_overlap ||
    topK !== kb.retrieval_top_k ||
    threshold !== kb.retrieval_score_threshold;

  const handleSave = () => {
    update.mutate({
      name,
      description,
      chunk_size: chunkSize,
      chunk_overlap: chunkOverlap,
      retrieval_top_k: topK,
      retrieval_score_threshold: threshold,
    });
  };

  const handleDelete = () => {
    if (confirmDelete) {
      destroy.mutate(kb.id, {
        onSuccess: () => router.push("/knowledge"),
      });
    } else {
      setConfirmDelete(true);
      setTimeout(() => setConfirmDelete(false), 3000);
    }
  };

  return (
    <>
      <div className="border-b border-border px-6 py-4">
        <h2 className="text-lg font-semibold">Settings</h2>
        <p className="mt-0.5 text-xs text-muted-foreground">
          Cập nhật thông tin và cấu hình retrieval. Lưu ý: đổi chunk size không tự re-process
          documents đã upload.
        </p>
      </div>

      <div className="scrollbar-thin flex-1 overflow-auto p-6">
        <div className="mx-auto max-w-3xl space-y-6">
          {/* Info */}
          <Section title="Information">
            <div className="space-y-1.5">
              <Label htmlFor="kb-name" className="text-xs">Name</Label>
              <Input id="kb-name" value={name} onChange={(e) => setName(e.target.value)} className="h-9 text-sm" />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="kb-desc" className="text-xs">Description</Label>
              <Textarea
                id="kb-desc"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={2}
                className="resize-none text-sm"
              />
            </div>
          </Section>

          {/* Chunking */}
          <Section title="Chunking">
            <SliderRow
              label="Chunk size"
              value={chunkSize}
              min={100}
              max={4000}
              step={50}
              onChange={setChunkSize}
              unit="chars"
            />
            <SliderRow
              label="Chunk overlap"
              value={chunkOverlap}
              min={0}
              max={Math.min(500, chunkSize - 1)}
              step={10}
              onChange={setChunkOverlap}
              unit="chars"
            />
          </Section>

          {/* Retrieval */}
          <Section title="Retrieval">
            <SliderRow label="Top K" value={topK} min={1} max={20} step={1} onChange={setTopK} />
            <SliderRow
              label="Score threshold"
              value={threshold}
              min={0}
              max={1}
              step={0.05}
              onChange={setThreshold}
              fixed={2}
            />
          </Section>

          {/* Embedding readonly */}
          <Section title="Embedding (read-only)">
            <div className="space-y-2 rounded-lg border border-border/70 bg-muted/30 p-3 text-xs">
              <Row label="Provider" value={<Badge variant="secondary">{kb.embedding_provider}</Badge>} />
              <Row label="Model" value={<span className="font-mono">{kb.embedding_model}</span>} />
              <Row label="Dimensions" value={<span className="font-mono">{kb.embedding_dimensions}</span>} />
              <p className="pt-1 text-[10px] text-muted-foreground">
                Embedding được snapshot lúc tạo KB — không đổi sau đó để giữ vector space nhất quán.
              </p>
            </div>
          </Section>

          {/* Save */}
          <div className="flex items-center justify-end border-t border-border pt-4">
            <Button size="sm" disabled={!dirty || update.isPending} onClick={handleSave} className="gap-1.5">
              {update.isPending ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Save className="h-3.5 w-3.5" />
              )}
              Save changes
            </Button>
          </div>

          {/* Danger zone */}
          <Section title="Danger Zone">
            <div className="flex items-start justify-between rounded-lg border border-destructive/30 bg-destructive/5 p-4">
              <div>
                <p className="text-sm font-medium">Delete knowledge</p>
                <p className="mt-0.5 text-[11px] text-muted-foreground">
                  Xoá knowledge này cùng toàn bộ document, chunk và embedding. Không thể khôi phục.
                </p>
              </div>
              <Button variant="destructive" size="sm" onClick={handleDelete} className="gap-1.5">
                <Trash2 className="h-3.5 w-3.5" />
                {confirmDelete ? "Click again to confirm" : "Delete"}
              </Button>
            </div>
          </Section>
        </div>
      </div>
    </>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section>
      <h3 className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
        {title}
      </h3>
      <div className="space-y-4 rounded-xl border border-border bg-card/80 p-5">{children}</div>
    </section>
  );
}

function SliderRow({
  label,
  value,
  min,
  max,
  step,
  onChange,
  unit,
  fixed = 0,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  onChange: (v: number) => void;
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
      <Slider min={min} max={max} step={step} value={[value]} onValueChange={(v) => onChange(v[0])} />
    </div>
  );
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-muted-foreground">{label}</span>
      <span>{value}</span>
    </div>
  );
}
