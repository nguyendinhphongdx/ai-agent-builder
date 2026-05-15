"use client";

import { useState } from "react";
import Link from "next/link";
import { Check, Plus, Wrench, Globe, Code, Database, Search } from "lucide-react";
import { useWorkspacePath } from "@/features/workspaces";
import { cn } from "@/lib/utils";

interface ToolItem {
  id: string;
  name: string;
  description: string;
  type: "system" | "custom";
  icon: "globe" | "code" | "database" | "wrench";
}

const SYSTEM_TOOLS: ToolItem[] = [
  {
    id: "web_search",
    name: "Web Search",
    description: "Search the web for real-time information",
    type: "system",
    icon: "globe",
  },
  {
    id: "code_exec",
    name: "Code Interpreter",
    description: "Execute Python code in a sandbox",
    type: "system",
    icon: "code",
  },
  {
    id: "web_scrape",
    name: "Web Scraper",
    description: "Extract content from web pages",
    type: "system",
    icon: "globe",
  },
];

const ICON_MAP = {
  globe: Globe,
  code: Code,
  database: Database,
  wrench: Wrench,
};

interface ToolsSelectorProps {
  selectedToolIds: string[];
  onToggle: (toolId: string) => void;
  customTools?: ToolItem[];
}

export function ToolsSelector({
  selectedToolIds,
  onToggle,
  customTools = [],
}: ToolsSelectorProps) {
  const wp = useWorkspacePath();
  const allTools = [...SYSTEM_TOOLS, ...customTools];

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <Link
          href={wp("/tools")}
          className="text-[11px] font-medium text-primary transition-colors hover:text-primary/80"
        >
          Manage tools →
        </Link>
      </div>

      <div className="space-y-1.5">
        {allTools.map((tool) => {
          const Icon = ICON_MAP[tool.icon];
          const isSelected = selectedToolIds.includes(tool.id);

          return (
            <button
              key={tool.id}
              type="button"
              onClick={() => onToggle(tool.id)}
              className={cn(
                "flex w-full items-center gap-3 rounded-lg border px-3 py-2.5 text-left transition-all",
                isSelected
                  ? "border-primary/40 bg-primary/8 shadow-sm"
                  : "border-border bg-background/60 hover:border-border/80 hover:bg-muted/50"
              )}
            >
              <div
                className={cn(
                  "flex h-7 w-7 shrink-0 items-center justify-center rounded-md border transition-colors",
                  isSelected
                    ? "border-primary/30 bg-primary/15"
                    : "border-border bg-muted/60"
                )}
              >
                <Icon
                  className={cn(
                    "h-3.5 w-3.5 transition-colors",
                    isSelected ? "text-primary" : "text-muted-foreground"
                  )}
                />
              </div>

              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-1.5">
                  <p className={cn("text-xs font-medium", isSelected ? "text-foreground" : "text-foreground/80")}>
                    {tool.name}
                  </p>
                  {tool.type === "system" && (
                    <span className="rounded bg-muted px-1 py-0.5 text-[9px] uppercase tracking-wider text-muted-foreground">
                      System
                    </span>
                  )}
                </div>
                <p className="mt-0.5 truncate text-[11px] text-muted-foreground">
                  {tool.description}
                </p>
              </div>

              <div
                className={cn(
                  "flex h-4 w-4 shrink-0 items-center justify-center rounded-full border transition-all",
                  isSelected
                    ? "border-primary bg-primary"
                    : "border-border bg-background"
                )}
              >
                {isSelected && <Check className="h-2.5 w-2.5 text-primary-foreground" />}
              </div>
            </button>
          );
        })}

        {allTools.length === 0 && (
          <p className="py-4 text-center text-xs text-muted-foreground">
            Chưa có tool nào. <Link href={wp("/tools")} className="text-primary hover:underline">Tạo tool mới</Link>
          </p>
        )}
      </div>
    </div>
  );
}
