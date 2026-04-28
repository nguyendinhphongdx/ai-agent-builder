"use client";

import { useState } from "react";
import { Check, Copy } from "lucide-react";
import { cn } from "@/lib/utils";

interface CodeBlockCopyProps {
  code: string;
  language?: string;
  /** Optional title shown above the code block (e.g. file path / shell prompt). */
  title?: string;
  className?: string;
}

/**
 * Plain code block with a copy button. No syntax highlighting yet — keeps the
 * bundle small and integration pages don't need rich highlighting. Swap for
 * shiki/prism later if needed.
 */
export function CodeBlockCopy({
  code,
  language,
  title,
  className,
}: CodeBlockCopyProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard denied — silently ignore */
    }
  };

  return (
    <div className={cn("overflow-hidden rounded-lg border border-border", className)}>
      {(title || language) && (
        <div className="flex items-center justify-between border-b border-border bg-muted/40 px-3 py-1.5">
          <span className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
            {title ?? language}
          </span>
          {language && title && (
            <span className="font-mono text-[10px] text-muted-foreground/60">
              {language}
            </span>
          )}
        </div>
      )}
      <div className="relative">
        <pre className="scrollbar-thin overflow-x-auto bg-card/80 px-4 py-3 text-xs leading-relaxed">
          <code className="font-mono">{code}</code>
        </pre>
        <button
          type="button"
          onClick={handleCopy}
          className={cn(
            "absolute right-2 top-2 flex h-7 items-center gap-1 rounded-md border border-border bg-background/90 px-2 text-[10px] font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-foreground",
          )}
          title={copied ? "Copied!" : "Copy"}
        >
          {copied ? (
            <>
              <Check className="h-3 w-3 text-emerald-500" />
              Copied
            </>
          ) : (
            <>
              <Copy className="h-3 w-3" />
              Copy
            </>
          )}
        </button>
      </div>
    </div>
  );
}
