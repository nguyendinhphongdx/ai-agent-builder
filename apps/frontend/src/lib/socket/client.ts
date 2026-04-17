import { io, type Socket } from "socket.io-client";

export function connectSocket(url: string, token: string): Socket {
  return io(url, {
    auth: { token },
    transports: ["websocket"],
    reconnection: true,
    reconnectionDelay: 1000,
    reconnectionAttempts: 10,
  });
}

export function disconnectSocket(socket: Socket): void {
  if (socket.connected) {
    socket.disconnect();
  }
}
