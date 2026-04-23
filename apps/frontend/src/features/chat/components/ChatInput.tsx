"use client";

import { useCallback, useRef, useState } from "react";
import { Paperclip, Send } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useAttachments } from "../hooks/useAttachments";
import { AttachmentStrip } from "./AttachmentStrip";
import type { MessageAttachment } from "../types";

interface ChatInputProps {
  /** ``attachmentIds`` are server file IDs of ready uploads. */
  onSend: (content: string, attachments: MessageAttachment[]) => void;
  disabled?: boolean;
}

// Union of every extension we accept. Images natively, docs via server-side
// extractors (text; OCR fallback later). Model-specific gating — if any —
// happens server-side.
const ACCEPT = [
  "image/jpeg",
  "image/png",
  "image/webp",
  "image/gif",
  ".pdf",
  ".docx",
  ".xlsx",
  ".pptx",
  ".txt",
  ".md",
  ".csv",
  ".html",
  ".htm",
].join(",");

// Must stay aligned with backend ``attachment`` upload config (10 MB).
const MAX_SIZE = 10 * 1024 * 1024;
const MAX_FILES = 10;

export function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [value, setValue] = useState("");
  const [isDragging, setIsDragging] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const dragCounterRef = useRef(0);

  const { attachments, isBusy, add, remove, clear, ready } = useAttachments();

  const validate = useCallback(
    (files: File[]): File[] => {
      const accepted: File[] = [];
      const room = MAX_FILES - attachments.length;
      if (files.length > room) {
        toast.warning(`Only ${room} more file${room === 1 ? "" : "s"} allowed`);
      }
      for (const file of files.slice(0, room)) {
        if (file.size > MAX_SIZE) {
          toast.error(`${file.name} is too large (max 10 MB)`);
          continue;
        }
        accepted.push(file);
      }
      return accepted;
    },
    [attachments.length],
  );

  const handlePickFiles = () => fileInputRef.current?.click();

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? []);
    const ok = validate(files);
    if (ok.length) add(ok);
    e.target.value = ""; // reset so the same file fires change again
  };

  // Drag-and-drop tolerates nested enter/leave via a counter.
  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.dataTransfer.types.includes("Files")) {
      dragCounterRef.current += 1;
      setIsDragging(true);
    }
  };
  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounterRef.current = Math.max(0, dragCounterRef.current - 1);
    if (dragCounterRef.current === 0) setIsDragging(false);
  };
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    e.dataTransfer.dropEffect = "copy";
  };
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounterRef.current = 0;
    setIsDragging(false);
    const files = Array.from(e.dataTransfer.files ?? []);
    const ok = validate(files);
    if (ok.length) add(ok);
  };

  const canSend =
    !disabled &&
    !isBusy &&
    (value.trim().length > 0 || attachments.some((a) => a.status === "ready"));

  const handleSubmit = () => {
    if (!canSend) return;
    onSend(value.trim(), ready());
    setValue("");
    clear();
    textareaRef.current?.focus();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  // Paste images/files from clipboard (screenshots, Finder copy, …).
  const handlePaste = (e: React.ClipboardEvent) => {
    const items = Array.from(e.clipboardData?.items ?? []);
    const files = items
      .filter((it) => it.kind === "file")
      .map((it) => it.getAsFile())
      .filter((f): f is File => f !== null);
    if (files.length === 0) return;
    e.preventDefault(); // only consume paste when there are actual files
    const ok = validate(files);
    if (ok.length) add(ok);
  };

  return (
    <div className="border-t border-border/70 bg-background/85 px-4 py-3 backdrop-blur">
      <div className="mx-auto max-w-3xl space-y-2">
        <div
          onDragEnter={handleDragEnter}
          onDragLeave={handleDragLeave}
          onDragOver={handleDragOver}
          onDrop={handleDrop}
          className={cn(
            "relative rounded-2xl border bg-card p-2 shadow-sm transition-shadow focus-within:shadow-md",
            isDragging ? "border-primary/60 ring-2 ring-primary/20" : "border-border",
          )}
        >
          {isDragging && (
            <div className="pointer-events-none absolute inset-0 z-10 flex items-center justify-center rounded-2xl bg-primary/5 text-xs font-medium text-primary">
              Drop to attach
            </div>
          )}

          <AttachmentStrip attachments={attachments} onRemove={remove} />

          <div className="flex items-end gap-2">
            <button
              type="button"
              onClick={handlePickFiles}
              disabled={disabled || attachments.length >= MAX_FILES}
              className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl text-muted-foreground transition-colors hover:bg-accent hover:text-foreground disabled:cursor-not-allowed disabled:opacity-50"
              aria-label="Attach files"
              title="Attach files"
            >
              <Paperclip className="h-4 w-4" />
            </button>

            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept={ACCEPT}
              className="hidden"
              onChange={handleFileChange}
            />

            <Textarea
              ref={textareaRef}
              value={value}
              onChange={(e) => setValue(e.target.value)}
              onKeyDown={handleKeyDown}
              onPaste={handlePaste}
              placeholder="Nhập prompt của bạn..."
              className="min-h-11.5 max-h-40 resize-none border-0 bg-transparent px-2 py-2 text-sm shadow-none focus-visible:border-0 focus-visible:ring-0"
              rows={1}
              disabled={disabled}
            />

            <Button
              onClick={handleSubmit}
              disabled={!canSend}
              size="icon"
              className="h-10 w-10 shrink-0 rounded-xl"
              title={isBusy ? "Wait for uploads to finish" : undefined}
            >
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </div>

        <p className="px-1 text-[11px] text-muted-foreground">
          Enter để gửi, Shift + Enter xuống dòng. Kéo thả hoặc Ctrl/⌘ + V để đính file.
        </p>
      </div>
    </div>
  );
}
