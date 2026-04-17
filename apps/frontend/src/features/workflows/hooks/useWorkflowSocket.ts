"use client";

import { useEffect } from "react";
import { useSocket } from "@/features/notifications/hooks/useSocket";
import { useWorkflowEditorStore } from "../stores/workflowEditorStore";
import type { SocketEnvelope } from "@/lib/socket/types";

/**
 * Join workflow room and listen to node execution events.
 * Updates nodeStatuses in store for real-time visual feedback on canvas.
 */
export function useWorkflowSocket(workflowId: string) {
  const { socket, isConnected } = useSocket();
  const { setNodeStatus, clearNodeStatuses } = useWorkflowEditorStore();

  useEffect(() => {
    if (!socket || !isConnected) return;

    const room = `workflow:${workflowId}`;

    // Join room
    socket.emit("join", { room });

    // Clear previous statuses
    clearNodeStatuses();

    // Listen to node events
    const onNodeRunning = (envelope: SocketEnvelope) => {
      const { nodeId } = envelope.payload as { nodeId: string };
      setNodeStatus(nodeId, "running");
    };

    const onNodeCompleted = (envelope: SocketEnvelope) => {
      const { nodeId } = envelope.payload as { nodeId: string };
      setNodeStatus(nodeId, "completed");
    };

    const onNodeFailed = (envelope: SocketEnvelope) => {
      const { nodeId } = envelope.payload as { nodeId: string };
      setNodeStatus(nodeId, "failed");
    };

    socket.on("node:running", onNodeRunning);
    socket.on("node:completed", onNodeCompleted);
    socket.on("node:failed", onNodeFailed);

    return () => {
      socket.emit("leave", { room });
      socket.off("node:running", onNodeRunning);
      socket.off("node:completed", onNodeCompleted);
      socket.off("node:failed", onNodeFailed);
    };
  }, [socket, isConnected, workflowId, setNodeStatus, clearNodeStatuses]);
}
