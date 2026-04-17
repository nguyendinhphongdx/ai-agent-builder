import { apiClient } from "@/lib/api/client";

interface SocketConnection {
  url: string;
  token: string;
}

export const socketService = {
  getConnection: () =>
    apiClient.get<SocketConnection>("/me/socket").then((r) => r.data),
};
