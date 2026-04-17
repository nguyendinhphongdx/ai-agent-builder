"use client";

import { useEffect, useRef, useState } from "react";
import type { Socket } from "socket.io-client";
import { connectSocket, disconnectSocket } from "@/lib/socket/client";
import { SocketContext } from "@/features/notifications/hooks/useSocket";
import { socketService } from "@/features/notifications/services/socketService";
import { useAuth } from "@/features/auth/hooks/useAuth";

export function SocketProvider({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth();
  const socketRef = useRef<Socket | null>(null);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    if (!isAuthenticated) {
      if (socketRef.current) {
        disconnectSocket(socketRef.current);
        socketRef.current = null;
        setIsConnected(false);
      }
      return;
    }

    // Fetch socket URL + token, then connect
    socketService.getConnection().then(({ url, token }) => {
      const socket = connectSocket(url, token);

      socket.on("connect", () => setIsConnected(true));
      socket.on("disconnect", () => setIsConnected(false));

      socketRef.current = socket;
    }).catch(() => {
      // Socket service might not be running - non-critical
    });

    return () => {
      if (socketRef.current) {
        disconnectSocket(socketRef.current);
        socketRef.current = null;
        setIsConnected(false);
      }
    };
  }, [isAuthenticated]);

  return (
    <SocketContext value={{ socket: socketRef.current, isConnected }}>
      {children}
    </SocketContext>
  );
}
