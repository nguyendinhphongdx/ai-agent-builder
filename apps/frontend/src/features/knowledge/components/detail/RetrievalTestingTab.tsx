"use client";

import { useState } from "react";
import { Search, Loader2, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { useQueryKnowledgeBase } from "../../hooks/useKnowledge";

interface RetrievalTestingTabProps {
  kbId: string;
}

export function RetrievalTestingTab({ kbId }: RetrievalTestingTabProps) {
  const [query, setQuery] = useState("");
  const mutation = useQueryKnowledgeBase(kbId);
  const results = mutation.data ?? [];

  const handleRun = () => {
    if (!query.trim()) return;
    mutation.mutate({ query: query.trim(), topK: 10 });
  };

  return (
    <>
      <div className="border-b border-border px-6 py-4">
        <h2 className="text-lg font-semibold">Retrieval Testing</h2>
        <p className="mt-0.5 text-xs text-muted-foreground">
          Test trực tiếp xem agent sẽ retrieve chunk nào cho 1 query cụ thể.
        </p>
      </div>

      <div className="scrollbar-thin flex-1 overflow-auto p-6">
        <div className="mx-auto max-w-3xl space-y-5">
          {/* Query input */}
          <div className="space-y-2">
            <label className="text-xs font-medium">Query</label>
            <Textarea
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Nhập câu hỏi test…"
              className="min-h-[96px] resize-none text-sm"
              onKeyDown={(e) => {
                if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) handleRun();
              }}
            />
            <div className="flex items-center justify-between text-[10px] text-muted-foreground">
              <span>⌘/Ctrl + Enter để chạy</span>
              <Button size="sm" onClick={handleRun} disabled={!query.trim() || mutation.isPending} className="gap-1.5">
                {mutation.isPending ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <Search className="h-3.5 w-3.5" />
                )}
                Run retrieval
              </Button>
            </div>
          </div>

          {/* Results */}
          {mutation.isError && (
            <div className="rounded-md border border-destructive/30 bg-destructive/5 px-4 py-3 text-xs text-destructive">
              {(mutation.error as Error)?.message ?? "Retrieval failed"}
            </div>
          )}

          {mutation.isSuccess && (
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-xs">
                <Sparkles className="h-3.5 w-3.5 text-primary" />
                <span className="font-medium">{results.length} matches</span>
              </div>

              {results.length === 0 ? (
                <p className="rounded-md border border-dashed border-border bg-muted/30 px-4 py-6 text-center text-xs text-muted-foreground">
                  Không có chunk nào đạt ngưỡng score. Thử giảm threshold trong Settings.
                </p>
              ) : (
                <div className="space-y-2.5">
                  {results.map((r, i) => (
                    <div
                      key={i}
                      className="rounded-lg border border-border bg-card/70 p-4 shadow-sm"
                    >
                      <div className="mb-2 flex items-center justify-between text-[10px] text-muted-foreground">
                        <span className="font-mono uppercase">Chunk #{i + 1}</span>
                        {r.score !== null && (
                          <Badge variant="secondary" className="px-1.5 py-0 text-[10px] font-mono">
                            score {r.score.toFixed(3)}
                          </Badge>
                        )}
                      </div>
                      <p className="whitespace-pre-wrap text-xs leading-relaxed">{r.content}</p>
                      {Object.keys(r.metadata).length > 0 && (
                        <div className="mt-2 flex flex-wrap gap-1 border-t border-border/60 pt-2">
                          {Object.entries(r.metadata).slice(0, 5).map(([k, v]) => (
                            <span
                              key={k}
                              className="rounded bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground"
                            >
                              {k}: {String(v).slice(0, 40)}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </>
  );
}
