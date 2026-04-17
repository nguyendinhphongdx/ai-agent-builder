"use client";

import { HttpConfigForm } from "./config/HttpConfigForm";
import { CodeConfigForm, CustomFunctionConfigForm } from "./config/CodeConfigForm";
import { WebScrapeConfigForm } from "./config/WebScrapeConfigForm";
import { DbConfigForm } from "./config/DbConfigForm";
import type { ToolType } from "../types";

interface ToolConfigRendererProps {
  toolType: ToolType;
  value: Record<string, unknown>;
  onChange: (value: Record<string, unknown>) => void;
}

export function ToolConfigRenderer({ toolType, value, onChange }: ToolConfigRendererProps) {
  switch (toolType) {
    case "http_request":
      return <HttpConfigForm value={value} onChange={onChange} />;
    case "code_exec":
      return <CodeConfigForm value={value} onChange={onChange} />;
    case "web_scrape":
      return <WebScrapeConfigForm value={value} onChange={onChange} />;
    case "db_query":
      return <DbConfigForm value={value} onChange={onChange} />;
    case "custom_function":
      return <CustomFunctionConfigForm value={value} onChange={onChange} />;
    default:
      return null;
  }
}
