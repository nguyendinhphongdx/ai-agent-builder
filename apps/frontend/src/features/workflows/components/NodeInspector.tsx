"use client";

import { createElement } from "react";
import { Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { getNodeEntry } from "../nodes/registry";
import type { NodeData } from "../nodes/types";
import { useWorkflowEditorStore } from "../stores/workflowEditorStore";

export function NodeInspector() {
  const { nodes, editingNodeId, editNode, updateNodeData, removeNode } =
    useWorkflowEditorStore();

  const node = nodes.find((n) => n.id === editingNodeId);
  const isOpen = !!node && !!editingNodeId;
  const entry = node ? getNodeEntry(node.data.nodeType as string) : null;
  const typeDef = entry?.definition ?? null;

  return (
    <Sheet open={isOpen} onOpenChange={(open) => !open && editNode(null)}>
      <SheetContent
        side="right"
        className="w-95 sm:max-w-95 overflow-auto"
      >
        {typeDef && entry && node && editingNodeId && (
          <>
            <SheetHeader>
              <div className="flex items-center gap-2.5">
                <div
                  className="flex h-8 w-8 items-center justify-center rounded-lg"
                  style={{ backgroundColor: `${typeDef.color}20` }}
                >
                  {createElement(typeDef.icon, {
                    className: "h-4 w-4",
                    style: { color: typeDef.color },
                  })}
                </div>
                <div>
                  <SheetTitle className="text-sm">
                    {(node.data.label as string) || typeDef.label}
                  </SheetTitle>
                  <p className="text-xs text-muted-foreground">{typeDef.type}</p>
                </div>
              </div>
            </SheetHeader>

            <div className="mt-6 space-y-5 px-4">
              {/* Label */}
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-muted-foreground">
                  Label
                </label>
                <Input
                  value={(node.data.label as string) || ""}
                  onChange={(e) =>
                    updateNodeData(editingNodeId, { label: e.target.value })
                  }
                  placeholder={typeDef.label}
                />
              </div>

              {/* Per-node panel */}
              {createElement(entry.panel, {
                id: editingNodeId,
                data: node.data as unknown as NodeData,
              })}

              {/* Delete */}
              {typeDef.canDelete !== false && (
                <div className="pt-4 border-t border-border">
                  <Button
                    variant="destructive"
                    size="sm"
                    className="w-full gap-1.5"
                    onClick={() => removeNode(editingNodeId)}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                    Delete Node
                  </Button>
                </div>
              )}
            </div>
          </>
        )}
      </SheetContent>
    </Sheet>
  );
}
