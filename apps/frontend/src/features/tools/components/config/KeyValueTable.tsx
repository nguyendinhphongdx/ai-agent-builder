"use client";

import { Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { type KVPair, newKvId } from "../../utils";

interface KeyValueTableProps {
  value: KVPair[];
  onChange: (value: KVPair[]) => void;
  keyPlaceholder?: string;
  valuePlaceholder?: string;
}

export function KeyValueTable({
  value,
  onChange,
  keyPlaceholder = "Header name",
  valuePlaceholder = "Value or {variable}",
}: KeyValueTableProps) {
  const addRow = () => {
    onChange([...value, { id: newKvId(), key: "", value: "", enabled: true }]);
  };

  const removeRow = (id: string) => {
    onChange(value.filter((r) => r.id !== id));
  };

  const updateRow = (id: string, patch: Partial<KVPair>) => {
    onChange(value.map((r) => (r.id === id ? { ...r, ...patch } : r)));
  };

  return (
    <div className="space-y-1.5">
      {value.length === 0 && (
        <p className="py-2 text-xs text-muted-foreground">No entries. Click + Add to add one.</p>
      )}
      {value.map((row) => (
        <div key={row.id} className="flex items-center gap-2">
          <Switch
            checked={row.enabled}
            onCheckedChange={(checked) => updateRow(row.id, { enabled: checked })}
            className="shrink-0"
          />
          <Input
            className="h-8 flex-1 font-mono text-xs"
            placeholder={keyPlaceholder}
            value={row.key}
            onChange={(e) => updateRow(row.id, { key: e.target.value })}
          />
          <span className="text-xs text-muted-foreground">:</span>
          <Input
            className="h-8 flex-2 font-mono text-xs"
            placeholder={valuePlaceholder}
            value={row.value}
            onChange={(e) => updateRow(row.id, { value: e.target.value })}
          />
          <Button
            type="button"
            size="icon"
            variant="ghost"
            className="h-7 w-7 shrink-0 text-muted-foreground hover:text-destructive"
            onClick={() => removeRow(row.id)}
          >
            <Trash2 className="h-3.5 w-3.5" />
          </Button>
        </div>
      ))}
      <Button
        type="button"
        size="sm"
        variant="outline"
        className="mt-1 h-7 gap-1 text-xs"
        onClick={addRow}
      >
        <Plus className="h-3 w-3" />
        Add
      </Button>
    </div>
  );
}
