"use client";

import { useEffect, useCallback } from "react";
import { useSocket } from "./useSocket";
import type { SocketEnvelope } from "@/lib/socket/types";

/**
 * Subscribe to a socket event. Handler called with payload when event fires.
 *
 * Usage:
 *   useSocketEvent("agent:complete", (payload) => {
 *     toast.success(`Agent ${payload.name} finished`);
 *   });
 */
export function useSocketEvent<T = Record<string, unknown>>(
  eventName: string,
  handler: (payload: T) => void,
) {
  const { socket } = useSocket();

  const stableHandler = useCallback(handler, [handler]);

  useEffect(() => {
    if (!socket) return;

    const cb = (envelope: SocketEnvelope) => {
      stableHandler(envelope.payload as T);
    };

    socket.on(eventName, cb);
    return () => {
      socket.off(eventName, cb);
    };
  }, [socket, eventName, stableHandler]);
}
