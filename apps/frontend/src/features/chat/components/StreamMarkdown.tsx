"use client";

import { Streamdown } from "streamdown";
import { cjk } from "@streamdown/cjk";
import { createCodePlugin } from "@streamdown/code";
import { createMathPlugin } from "@streamdown/math";
import { createMermaidPlugin } from "@streamdown/mermaid";

interface StreamMarkdownProps {
  content: string;
  mode?: "static" | "streaming";
}

const code = createCodePlugin({
  themes: ["github-light", "github-dark"],
});

const math = createMathPlugin({
  singleDollarTextMath: false,
  errorColor: "#dc2626",
});

const mermaid = createMermaidPlugin({
  config: {
    theme: "neutral",
  },
});


export function StreamMarkdown({ content, mode = "static" }: StreamMarkdownProps) {
  return (
    <div className="min-w-0 max-w-none text-sm leading-relaxed text-foreground [&_a]:text-primary [&_a]:no-underline hover:[&_a]:underline [&_p]:my-3 [&_p:first-child]:mt-0 [&_p:last-child]:mb-0 [&_ul]:my-3 [&_ol]:my-3 [&_li]:my-1 [&_blockquote]:border-l-2 [&_blockquote]:border-border [&_blockquote]:pl-4 [&_blockquote]:text-muted-foreground [&_pre]:overflow-x-auto">
      <Streamdown
        mode={mode}
        plugins={{ code, math, cjk, mermaid }}
        controls={{
          code: { copy: true, download: true },
        }}
        isAnimating={mode === "streaming"}
        lineNumbers={false}
      >
        {content}
      </Streamdown>
    </div>
  );
}
