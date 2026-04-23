"use client";

import { FileText, Loader2, X, AlertCircle, Image as ImageIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import type { Attachment } from "../hooks/useAttachments";

interface AttachmentStripProps {
  attachments: Attachment[];
  onRemove: (id: string) => void;
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function AttachmentCard({ att, onRemove }: { att: Attachment; onRemove: (id: string) => void }) {
  const isImage = att.mimeType.startsWith("image/");
  const isUploading = att.status === "uploading";
  const isFailed = att.status === "failed";

  return (
    <div
      className={cn(
        "group relative flex items-center gap-2.5 overflow-hidden rounded-xl border bg-card px-2 py-1.5 text-xs shadow-sm",
        "min-w-40 max-w-56",
        isFailed
          ? "border-destructive/40 bg-destructive/5"
          : "border-border",
      )}
    >
      {/* Preview / icon */}
      <div className="relative flex h-9 w-9 shrink-0 items-center justify-center overflow-hidden rounded-lg bg-muted">
        {isImage && att.previewUrl ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={att.previewUrl}
            alt={att.file.name}
            className="h-full w-full object-cover"
          />
        ) : isImage ? (
          <ImageIcon className="h-4 w-4 text-muted-foreground" />
        ) : (
          <FileText className="h-4 w-4 text-muted-foreground" />
        )}

        {/* Progress overlay */}
        {isUploading && (
          <div className="absolute inset-0 flex items-center justify-center bg-background/70 backdrop-blur-[1px]">
            <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" />
          </div>
        )}
        {isFailed && (
          <div className="absolute inset-0 flex items-center justify-center bg-destructive/20">
            <AlertCircle className="h-3.5 w-3.5 text-destructive" />
          </div>
        )}
      </div>

      {/* Info */}
      <div className="min-w-0 flex-1">
        <p className="truncate text-[11px] font-medium text-foreground" title={att.file.name}>
          {att.file.name}
        </p>
        <p className="text-[10px] text-muted-foreground">
          {isUploading
            ? `${att.progress}%`
            : isFailed
              ? att.error ?? "Upload failed"
              : formatSize(att.file.size)}
        </p>
      </div>

      {/* Remove */}
      <button
        type="button"
        onClick={() => onRemove(att.id)}
        className="flex h-5 w-5 shrink-0 items-center justify-center rounded-md text-muted-foreground opacity-0 transition-opacity hover:bg-accent hover:text-foreground group-hover:opacity-100"
        aria-label="Remove attachment"
      >
        <X className="h-3 w-3" />
      </button>

      {/* Progress bar — bottom */}
      {isUploading && (
        <div className="absolute inset-x-0 bottom-0 h-0.5 bg-muted">
          <div
            className="h-full bg-primary transition-all"
            style={{ width: `${att.progress}%` }}
          />
        </div>
      )}
    </div>
  );
}

export function AttachmentStrip({ attachments, onRemove }: AttachmentStripProps) {
  if (attachments.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-2 px-1 pb-1">
      {attachments.map((att) => (
        <AttachmentCard key={att.id} att={att} onRemove={onRemove} />
      ))}
    </div>
  );
}
