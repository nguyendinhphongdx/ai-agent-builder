import { StickyNote } from "lucide-react";
import type { NodeTypeDefinition } from "../types";
import NotePanel from "./panel";
import NoteContent from "./node";

export const definition: NodeTypeDefinition = {
  type: "note",
  label: "Sticky Note",
  description: "Annotation that doesn't participate in execution",
  icon: StickyNote,
  color: "#f59e0b",
  category: "flow",
  handles: { inputs: [], outputs: [] },
  defaultData: () => ({ content: "" }),
};

export const NodeComponent = NoteContent;
export const PanelComponent = NotePanel;
