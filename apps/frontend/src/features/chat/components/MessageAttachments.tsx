"use client";

import { FileText, Image as ImageIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import type { MessageAttachment } from "../types";

interface MessageAttachmentsProps {
  attachments: MessageAttachment[];
  /** End-aligned (user messages show on the right). */
  align?: "start" | "end";
}

function extLabel(att: MessageAttachment): string {
  const parts = att.file_name.split(".");
  const ext = parts.length > 1 ? parts.pop()! : "";
  return ext.toUpperCase() || (att.mime_type?.split("/")[1] ?? "").toUpperCase();
}

function humanSize(bytes: number | null | undefined): string {
  if (!bytes) return "";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function AttachmentTile({ att }: { att: MessageAttachment }) {
  const isImage = att.mime_type?.startsWith("image/") ?? false;

  // Image tiles are square-ish thumbnails. Docs are wider cards with meta.
  if (isImage) {
    return (
      <div
        className="flex h-8 w-8 shrink-0 items-center justify-center overflow-hidden rounded-xl border border-border bg-muted"
        title={att.file_name}
      >
        <ImageIcon className="h-5 w-5 text-muted-foreground" />
      </div>
    );
  }

  const ext = extLabel(att);
  const size = humanSize(att.size);

  return (
    <div
      className="flex h-10 w-56 shrink-0 items-center gap-3 overflow-hidden rounded-xl border border-border bg-background px-3 py-2 shadow-sm"
      title={att.file_name}
    >
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
        <FileText className="h-4 w-4" />
      </div>
      <div className="min-w-0 flex-1 leading-tight">
        <p className="truncate text-[11px] font-medium text-foreground">
          {att.file_name}
        </p>
        <p className="text-[9px] mt-[2px] text-muted-foreground">
          {ext}
          {size && ` · ${size}`}
        </p>
      </div>
    </div>
  );
}

export function MessageAttachments({ attachments, align = "start" }: MessageAttachmentsProps) {

  if (!attachments?.length) return null;
  return (
    <div
      className={cn(
        "flex flex-wrap gap-2",
        align === "end" && "justify-end",
      )}
    >
      {attachments.map((att) => (
        <AttachmentTile key={att.id} att={att} />
      ))}
    </div>
  );
}
