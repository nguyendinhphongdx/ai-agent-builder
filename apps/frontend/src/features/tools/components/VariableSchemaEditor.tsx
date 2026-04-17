"use client";

import { useEffect, useMemo, useState } from "react";
import { Variable, Plus, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { extractConfigVariables, newKvId } from "../utils";
import type { JsonSchema } from "../types";

interface VariableEntry {
  id: string;
  name: string;
  description: string;
  auto: boolean; // detected from template vs manually added
}

interface VariableSchemaEditorProps {
  config: Record<string, unknown>;
  value: JsonSchema;
  onChange: (schema: JsonSchema) => void;
}

export function VariableSchemaEditor({ config, value, onChange }: VariableSchemaEditorProps) {
  const detectedNames = useMemo(() => extractConfigVariables(config), [config]);

  const [entries, setEntries] = useState<VariableEntry[]>(() => {
    const props = value.properties ?? {};
    const existingNames = Object.keys(props);
    const allNames = [...new Set([...detectedNames, ...existingNames])];
    return allNames.map((name) => ({
      id: newKvId(),
      name,
      description: (props[name]?.description as string) ?? "",
      auto: detectedNames.includes(name),
    }));
  });

  // Sync detected vars when config changes
  useEffect(() => {
    setEntries((prev) => {
      const prevNames = new Set(prev.map((e) => e.name));
      const result: VariableEntry[] = [];

      // Keep all existing (auto or manual)
      for (const e of prev) {
        result.push({ ...e, auto: detectedNames.includes(e.name) });
      }

      // Add newly detected ones not yet in the list
      for (const name of detectedNames) {
        if (!prevNames.has(name)) {
          result.push({ id: newKvId(), name, description: "", auto: true });
        }
      }

      // Mark auto ones that no longer appear in config
      return result;
    });
  }, [detectedNames.join(",")]);

  // Rebuild schema whenever entries change
  useEffect(() => {
    const properties: Record<string, { type: string; description?: string }> = {};
    for (const e of entries) {
      if (e.name.trim()) {
        properties[e.name.trim()] = {
          type: "string",
          ...(e.description ? { description: e.description } : {}),
        };
      }
    }
    onChange({
      type: "object",
      properties,
      required: entries.filter((e) => e.name.trim()).map((e) => e.name.trim()),
    });
  }, [entries]);

  const updateEntry = (id: string, patch: Partial<VariableEntry>) => {
    setEntries((prev) => prev.map((e) => (e.id === id ? { ...e, ...patch } : e)));
  };

  const removeEntry = (id: string) => {
    setEntries((prev) => prev.filter((e) => e.id !== id));
  };

  const addEntry = () => {
    setEntries((prev) => [...prev, { id: newKvId(), name: "", description: "", auto: false }]);
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <Variable className="h-3.5 w-3.5 text-muted-foreground" />
        <h3 className="text-xs font-semibold">Input variables</h3>
        <span className="ml-auto text-[11px] text-muted-foreground">
          {entries.length} variable{entries.length !== 1 ? "s" : ""}
        </span>
      </div>

      <p className="text-[11px] text-muted-foreground">
        Variables auto-detected from your config. Add descriptions so the LLM knows how to fill
        them.
      </p>

      {entries.length === 0 && (
        <p className="rounded-md border border-dashed border-border py-4 text-center text-xs text-muted-foreground">
          No variables yet. Use <code className="bg-muted rounded px-1">{"{name}"}</code> in your
          config to auto-detect them.
        </p>
      )}

      <div className="space-y-2">
        {entries.map((entry) => (
          <div key={entry.id} className="flex items-start gap-2">
            <div className="flex-1 space-y-1">
              <div className="flex items-center gap-1.5">
                <code className="rounded bg-primary/10 px-2 py-0.5 text-[11px] font-mono text-primary">
                  {"{"}
                  {entry.name || "…"}
                  {"}"}
                </code>
                {entry.auto && (
                  <Badge
                    variant="secondary"
                    className="h-4 border-0 bg-primary/10 px-1 text-[9px] text-primary"
                  >
                    auto
                  </Badge>
                )}
                {!entry.auto && (
                  <Input
                    className="h-6 w-36 font-mono text-[11px]"
                    placeholder="variable_name"
                    value={entry.name}
                    onChange={(e) => updateEntry(entry.id, { name: e.target.value })}
                  />
                )}
              </div>
              <Input
                className="h-7 text-xs"
                placeholder="Description for the LLM (e.g. 'User search query')"
                value={entry.description}
                onChange={(e) => updateEntry(entry.id, { description: e.target.value })}
              />
            </div>
            <Button
              type="button"
              size="icon"
              variant="ghost"
              className="mt-0.5 h-7 w-7 shrink-0 text-muted-foreground hover:text-destructive"
              onClick={() => removeEntry(entry.id)}
            >
              <X className="h-3.5 w-3.5" />
            </Button>
          </div>
        ))}
      </div>

      <Button
        type="button"
        size="sm"
        variant="outline"
        className="h-7 gap-1 text-xs"
        onClick={addEntry}
      >
        <Plus className="h-3 w-3" />
        Add variable
      </Button>
    </div>
  );
}
