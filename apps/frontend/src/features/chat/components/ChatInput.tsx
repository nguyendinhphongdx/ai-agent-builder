"use client";

import { useState, useRef } from "react";
import { Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

interface ChatInputProps {
  onSend: (content: string) => void;
  disabled?: boolean;
}

export function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = () => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue("");
    textareaRef.current?.focus();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="border-t border-border/70 bg-background/85 px-4 py-3 backdrop-blur">
      <div className="mx-auto max-w-3xl space-y-2">
        <div className="flex items-end gap-2 rounded-2xl border border-border bg-card p-2 shadow-sm transition-shadow focus-within:shadow-md">
          <Textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Nhập prompt của bạn..."
            className="min-h-11.5 max-h-40 resize-none border-0 bg-transparent px-2 py-2 text-sm shadow-none focus-visible:border-0 focus-visible:ring-0"
            rows={1}
            disabled={disabled}
          />
          <Button
            onClick={handleSubmit}
            disabled={disabled || !value.trim()}
            size="icon"
            className="h-10 w-10 shrink-0 rounded-xl"
          >
            <Send className="h-4 w-4" />
          </Button>
        </div>
        <p className="px-1 text-[11px] text-muted-foreground">
          Enter để gửi, Shift + Enter để xuống dòng.
        </p>
      </div>
    </div>
  );
}
