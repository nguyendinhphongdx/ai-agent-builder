"use client";

import { useState } from "react";
import { Loader2, Send } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { usePublishVersion } from "../hooks/useTemplates";

interface PublishVersionDialogProps {
  templateId: string;
  templateTitle: string;
  currentVersion: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const BUMP_OPTIONS = [
  {
    value: "patch",
    label: "Patch",
    hint: "small fixes — same behaviour",
    suffix: ".+1",
  },
  {
    value: "minor",
    label: "Minor",
    hint: "new features — backwards compatible",
    suffix: ".0",
  },
  {
    value: "major",
    label: "Major",
    hint: "breaking changes",
    suffix: "→ next.0.0",
  },
] as const;

export function PublishVersionDialog({
  templateId,
  templateTitle,
  currentVersion,
  open,
  onOpenChange,
}: PublishVersionDialogProps) {
  const publish = usePublishVersion(templateId);
  const [bump, setBump] = useState<"patch" | "minor" | "major">("patch");
  const [changelog, setChangelog] = useState("");

  const handleSubmit = () => {
    publish.mutate(
      { bump, changelog: changelog.trim() || undefined },
      { onSuccess: () => onOpenChange(false) },
    );
  };

  const nextPreview = previewBump(currentVersion ?? "0.0.0", bump);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Publish new version</DialogTitle>
          <DialogDescription>
            Re-snapshot <span className="font-medium">{templateTitle}</span>{" "}
            from your current agent. Existing forks keep their version pointer
            — only new forks pick up the new snapshot.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Bump selector */}
          <div className="space-y-2">
            <label className="text-xs font-medium text-muted-foreground">
              Version bump
            </label>
            <div className="grid grid-cols-3 gap-2">
              {BUMP_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => setBump(opt.value)}
                  className={`flex flex-col gap-1 rounded-lg border p-3 text-left text-xs transition-colors ${
                    bump === opt.value
                      ? "border-violet-500 bg-violet-500/5"
                      : "border-border hover:bg-accent"
                  }`}
                >
                  <span className="font-medium">{opt.label}</span>
                  <span className="text-[10px] text-muted-foreground">
                    {opt.hint}
                  </span>
                </button>
              ))}
            </div>
            <p className="text-[11px] text-muted-foreground">
              {currentVersion ? `Current: ${currentVersion}` : "First version"} →{" "}
              <span className="font-mono font-medium text-foreground">{nextPreview}</span>
            </p>
          </div>

          {/* Changelog */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground">
              Changelog (optional)
            </label>
            <Textarea
              value={changelog}
              onChange={(e) => setChangelog(e.target.value)}
              placeholder="What changed in this version?"
              rows={4}
              maxLength={5000}
            />
          </div>

          {publish.isError && (
            <p className="rounded-md border border-red-500/30 bg-red-500/5 p-2.5 text-[11px] text-red-700 dark:text-red-300">
              {(publish.error as Error)?.message ?? "Publish failed"}
            </p>
          )}
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={publish.isPending}
          >
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={publish.isPending}
            className="gap-1.5"
          >
            {publish.isPending ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Send className="h-3.5 w-3.5" />
            )}
            Publish {nextPreview}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function previewBump(current: string, bump: "patch" | "minor" | "major"): string {
  const parts = current.split(".").map(Number);
  if (parts.length < 3 || parts.some(Number.isNaN)) return `${current}.1`;
  const [major, minor, patch] = parts as [number, number, number];
  if (bump === "major") return `${major + 1}.0.0`;
  if (bump === "minor") return `${major}.${minor + 1}.0`;
  return `${major}.${minor}.${patch + 1}`;
}
