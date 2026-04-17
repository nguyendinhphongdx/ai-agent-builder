import { apiClient } from "@/lib/api/client";
import type { AuthResponse, LoginInput, RegisterInput, User } from "../types";

export const authService = {
  login: (data: LoginInput) =>
    apiClient.post<AuthResponse>("/auth/login", data).then((r) => r.data),

  register: (data: RegisterInput) =>
    apiClient.post<AuthResponse>("/auth/register", data).then((r) => r.data),

  logout: () => apiClient.post("/auth/logout"),

  getMe: () => apiClient.get<User>("/auth/me").then((r) => r.data),
};
