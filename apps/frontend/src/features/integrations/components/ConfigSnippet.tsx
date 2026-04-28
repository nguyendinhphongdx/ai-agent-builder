"use client";

import { useMemo } from "react";
import { CodeBlockCopy } from "./CodeBlockCopy";

interface ConfigSnippetProps {
  /** Template with ``{{var}}`` placeholders. */
  template: string;
  /** Map of var name → value. ``undefined`` falls back to ``— missing —``. */
  vars: Record<string, string | undefined | null>;
  language?: string;
  title?: string;
  className?: string;
}

/**
 * Renders a config/code template with values from ``vars`` interpolated in
 * for the user's actual token / URL. Missing values fall back to a visible
 * placeholder so the user knows what to fix instead of silently shipping
 * an empty value.
 */
export function ConfigSnippet({
  template,
  vars,
  language,
  title,
  className,
}: ConfigSnippetProps) {
  const code = useMemo(
    () =>
      template.replace(/\{\{\s*(\w+)\s*\}\}/g, (_, name: string) => {
        const v = vars[name];
        if (v === undefined || v === null || v === "") {
          return `<MISSING_${name.toUpperCase()}>`;
        }
        return v;
      }),
    [template, vars],
  );

  return (
    <CodeBlockCopy code={code} language={language} title={title} className={className} />
  );
}
