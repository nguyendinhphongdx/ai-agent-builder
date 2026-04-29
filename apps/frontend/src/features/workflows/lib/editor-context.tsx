"use client";

import { createContext, useContext, useMemo, type ReactNode } from "react";

interface WorkflowEditorContextValue {
  workflowId: string;
}

const WorkflowEditorContext = createContext<WorkflowEditorContextValue | null>(null);

/**
 * Carries the current workflow id down to deeply-nested editor pieces (NDV
 * panels, ExpressionField) without prop-drilling. Anything that already
 * receives `workflowId` as a prop should keep doing so — this is for sub-trees
 * that don't have a clean prop path.
 */
export function WorkflowEditorProvider({
  workflowId,
  children,
}: {
  workflowId: string;
  children: ReactNode;
}) {
  const value = useMemo(() => ({ workflowId }), [workflowId]);
  return (
    <WorkflowEditorContext.Provider value={value}>
      {children}
    </WorkflowEditorContext.Provider>
  );
}

export function useWorkflowEditorContext(): WorkflowEditorContextValue {
  const ctx = useContext(WorkflowEditorContext);
  if (!ctx) {
    throw new Error(
      "useWorkflowEditorContext must be used inside <WorkflowEditorProvider>",
    );
  }
  return ctx;
}

/** Optional variant — returns null instead of throwing when outside provider. */
export function useOptionalWorkflowEditorContext(): WorkflowEditorContextValue | null {
  return useContext(WorkflowEditorContext);
}
