"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Search, X, ChevronLeft, ChevronRight } from "lucide-react";
import { getAllDefinitions, getNodeEntry, getDefinitionsByCategory } from "../nodes/registry";
import { NODE_CATEGORIES } from "../nodes/types";
import type { NodeCategory, NodeTypeDefinition } from "../nodes/types";
import { useWorkflowEditorStore } from "../stores/workflowEditorStore";

export function NodePalette() {
  const {
    nodes,
    nodePaletteOpen: open,
    addNodeContext,
    closeNodePalette,
    addNode,
    onConnect,
  } = useWorkflowEditorStore();

  const [search, setSearch] = useState("");
  const [activeCategory, setActiveCategory] = useState<NodeCategory | null>(null);
  const searchRef = useRef<HTMLInputElement>(null);

  // Reset state when panel opens
  useEffect(() => {
    if (open) {
      setSearch("");
      setActiveCategory(null);
      const t = setTimeout(() => searchRef.current?.focus(), 100);
      return () => clearTimeout(t);
    }
  }, [open]);

  // Close on Escape, back on Escape in category
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        if (activeCategory) {
          setActiveCategory(null);
        } else {
          closeNodePalette();
        }
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [open, activeCategory, closeNodePalette]);

  const handleAddNode = useCallback(
    (type: string) => {
      const entry = getNodeEntry(type);
      const defaultData = entry?.definition.defaultData?.() ?? {};
      const newNodeId = crypto.randomUUID();

      let position = { x: 250 + Math.random() * 200, y: 150 + Math.random() * 200 };
      if (addNodeContext) {
        const sourceNode = nodes.find((n) => n.id === addNodeContext.sourceNodeId);
        if (sourceNode) {
          position = {
            x: sourceNode.position.x + (sourceNode.measured?.width ?? 160) + 80,
            y: sourceNode.position.y,
          };
        }
      }

      addNode({
        id: newNodeId,
        type: "baseNode",
        position,
        data: { nodeType: type, label: "", config: defaultData },
      });

      if (addNodeContext) {
        const targetEntry = getNodeEntry(type);
        const firstInput = targetEntry?.definition.handles.inputs[0];
        if (firstInput) {
          onConnect({
            source: addNodeContext.sourceNodeId,
            target: newNodeId,
            sourceHandle: addNodeContext.sourceHandleId,
            targetHandle: firstInput.id,
          });
        }
      }

      closeNodePalette();
    },
    [nodes, addNodeContext, addNode, onConnect, closeNodePalette]
  );

  // Search: filter all nodes across categories
  const allDefs = getAllDefinitions();
  const searchResults = search
    ? allDefs.filter(
        (def) =>
          def.label.toLowerCase().includes(search.toLowerCase()) ||
          def.description.toLowerCase().includes(search.toLowerCase())
      )
    : [];

  // Category nodes
  const categoryNodes = activeCategory ? getDefinitionsByCategory(activeCategory) : [];
  const activeCategoryMeta = activeCategory
    ? NODE_CATEGORIES.find((c) => c.key === activeCategory)
    : null;

  return (
    <>
      {/* Backdrop */}
      {open && <div className="absolute inset-0 z-40" onClick={closeNodePalette} />}

      {/* Panel */}
      <div
        className={`absolute right-0 top-0 z-50 flex h-full w-80 flex-col border-l border-border bg-card shadow-xl transition-transform duration-200 ease-out ${
          open ? "translate-x-0" : "translate-x-full"
        }`}
      >
        {/* Header */}
        <div className="flex items-center gap-2 border-b border-border px-4 py-3">
          {activeCategory && !search ? (
            <button
              onClick={() => setActiveCategory(null)}
              className="rounded-md p-1 text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
          ) : null}

          <div className="flex-1 min-w-0">
            {activeCategory && !search && activeCategoryMeta ? (
              <div className="flex items-center gap-2">
                <activeCategoryMeta.icon className="h-4 w-4 text-muted-foreground" />
                <p className="text-sm font-semibold text-foreground">
                  {activeCategoryMeta.label}
                </p>
              </div>
            ) : (
              <p className="text-sm font-semibold text-foreground">
                {addNodeContext ? "What happens next?" : "Add Node"}
              </p>
            )}
          </div>

          <button
            onClick={closeNodePalette}
            className="rounded-md p-1 text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Search */}
        <div className="border-b border-border px-3 py-2">
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
            <input
              ref={searchRef}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search nodes..."
              className="w-full rounded-md border border-border bg-background py-1.5 pl-8 pr-3 text-xs outline-none placeholder:text-muted-foreground focus:border-primary focus:ring-1 focus:ring-primary/30"
            />
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto">
          {search ? (
            // Search results — flat node list
            <NodeList
              nodes={searchResults}
              onSelect={handleAddNode}
              onClose={closeNodePalette}
              emptyMessage="No nodes found"
            />
          ) : activeCategory ? (
            // Category drill-down — node list for selected category
            <NodeList
              nodes={categoryNodes}
              onSelect={handleAddNode}
              onClose={closeNodePalette}
              emptyMessage="No nodes in this category"
            />
          ) : (
            // Category list — n8n style
            <div className="p-2 space-y-0.5">
              {NODE_CATEGORIES.map((cat) => {
                const count = getDefinitionsByCategory(cat.key).length;
                const Icon = cat.icon;
                return (
                  <button
                    key={cat.key}
                    onClick={() => setActiveCategory(cat.key)}
                    className="flex w-full items-center gap-3 rounded-lg px-3 py-3 text-left transition-colors hover:bg-accent group"
                  >
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-muted">
                      <Icon className="h-4 w-4 text-muted-foreground" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-medium text-foreground">
                        {cat.label}
                      </p>
                      <p className="text-[10px] text-muted-foreground truncate">
                        {cat.description}
                      </p>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <span className="text-[10px] text-muted-foreground">{count}</span>
                      <ChevronRight className="h-3.5 w-3.5 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </>
  );
}

// --- Node list sub-component ---

function NodeList({
  nodes,
  onSelect,
  onClose,
  emptyMessage,
}: {
  nodes: NodeTypeDefinition[];
  onSelect: (type: string) => void;
  onClose: () => void;
  emptyMessage: string;
}) {
  if (nodes.length === 0) {
    return (
      <p className="px-3 py-6 text-center text-xs text-muted-foreground">
        {emptyMessage}
      </p>
    );
  }

  return (
    <div className="p-2 space-y-0.5">
      {nodes.map((def) => {
        const Icon = def.icon;
        return (
          <button
            key={def.type}
            onClick={() => onSelect(def.type)}
            draggable
            onDragStart={(e) => {
              e.dataTransfer.setData("nodeType", def.type);
              e.dataTransfer.effectAllowed = "move";
              onClose();
            }}
            className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left transition-colors hover:bg-accent active:bg-accent/80"
          >
            <div
              className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md"
              style={{ backgroundColor: `${def.color}15` }}
            >
              <Icon className="h-3.5 w-3.5" style={{ color: def.color }} />
            </div>
            <div className="min-w-0">
              <p className="text-xs font-medium text-foreground">{def.label}</p>
              <p className="text-[10px] text-muted-foreground truncate">
                {def.description}
              </p>
            </div>
          </button>
        );
      })}
    </div>
  );
}
