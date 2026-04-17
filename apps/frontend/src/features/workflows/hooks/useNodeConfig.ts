import { useCallback } from "react";
import { useWorkflowEditorStore } from "../stores/workflowEditorStore";

export function useNodeConfig(nodeId: string) {
  const updateNodeData = useWorkflowEditorStore((s) => s.updateNodeData);
  const node = useWorkflowEditorStore((s) =>
    s.nodes.find((n) => n.id === nodeId)
  );
  const config = (node?.data.config as Record<string, unknown>) || {};

  const updateConfig = useCallback(
    (key: string, value: unknown) => {
      updateNodeData(nodeId, {
        config: { ...config, [key]: value },
      });
    },
    [nodeId, config, updateNodeData]
  );

  return { config, updateConfig };
}
