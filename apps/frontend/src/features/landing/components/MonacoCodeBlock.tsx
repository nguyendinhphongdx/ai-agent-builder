"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import { useTheme } from "next-themes";
import { Check, Copy } from "lucide-react";
import type { IntegrationPath } from "../data/content";

// Monaco is heavy (~5MB) — load it on the client only, after the rest of the
// page has rendered. The skeleton matches the editor's rendered height to
// avoid layout shift.
const Editor = dynamic(() => import("@monaco-editor/react").then((m) => m.Editor), {
  ssr: false,
  loading: () => <div className="h-72 w-full bg-muted/30" aria-hidden="true" />,
});

interface Props {
  path: IntegrationPath;
}

const HEIGHT = 280;

export function MonacoCodeBlock({ path }: Props) {
  const { resolvedTheme } = useTheme();
  const [copied, setCopied] = useState(false);

  const onCopy = async () => {
    try {
      await navigator.clipboard.writeText(path.code);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard may be blocked */
    }
  };

  return (
    <div className="overflow-hidden rounded-xl border border-border bg-background shadow-sm">
      {/* Editor chrome — file tab + actions */}
      <div className="flex items-center justify-between border-b border-border bg-muted/40 px-3 py-2">
        <div className="flex items-center gap-2">
          {/* Window dots — purely decorative */}
          <div className="flex gap-1.5">
            <div className="h-2.5 w-2.5 rounded-full bg-rose-400/80" />
            <div className="h-2.5 w-2.5 rounded-full bg-amber-400/80" />
            <div className="h-2.5 w-2.5 rounded-full bg-emerald-400/80" />
          </div>
          <div className="ml-2 inline-flex items-center gap-2 rounded-md bg-background px-2.5 py-1 font-mono text-[12px] text-muted-foreground">
            <span className="font-medium text-foreground">{path.filename}</span>
            <span className="rounded bg-muted px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
              {path.language}
            </span>
          </div>
        </div>
        <button
          type="button"
          onClick={onCopy}
          aria-label="Copy code"
          className="inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-xs text-muted-foreground transition-colors hover:bg-background hover:text-foreground"
        >
          {copied ? (
            <>
              <Check className="h-3.5 w-3.5 text-emerald-500" />
              Copied
            </>
          ) : (
            <>
              <Copy className="h-3.5 w-3.5" />
              Copy
            </>
          )}
        </button>
      </div>

      {/* Monaco editor */}
      <div style={{ height: HEIGHT }}>
        <Editor
          height={HEIGHT}
          language={path.language}
          value={path.code}
          theme={resolvedTheme === "dark" ? "vs-dark" : "light"}
          options={{
            readOnly: true,
            domReadOnly: true,
            minimap: { enabled: false },
            scrollBeyondLastLine: false,
            fontSize: 13,
            fontFamily:
              "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
            lineNumbers: "on",
            lineNumbersMinChars: 3,
            glyphMargin: false,
            folding: false,
            renderLineHighlight: "none",
            overviewRulerLanes: 0,
            hideCursorInOverviewRuler: true,
            overviewRulerBorder: false,
            scrollbar: { vertical: "auto", horizontal: "auto" },
            padding: { top: 14, bottom: 14 },
            wordWrap: "on",
            contextmenu: false,
            stickyScroll: { enabled: false },
            guides: { indentation: false },
          }}
        />
      </div>
    </div>
  );
}
