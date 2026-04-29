import { TextareaField } from "../../components/node-inspector/fields";
import { useNodeConfig } from "../../hooks/useNodeConfig";
import type { PanelProps } from "../types";

export default function NotePanel({ id }: PanelProps) {
  const { config, updateConfig } = useNodeConfig(id);

  return (
    <div className="space-y-3">
      <TextareaField
        label="Content"
        value={(config.content as string) || ""}
        onChange={(v) => updateConfig("content", v)}
        placeholder="Notes are visible on the canvas only — they aren't sent to executors."
      />
      <p className="text-[11px] text-muted-foreground">
        Sticky notes have no inputs or outputs. Resize from the corners when the
        note is selected on the canvas.
      </p>
    </div>
  );
}
