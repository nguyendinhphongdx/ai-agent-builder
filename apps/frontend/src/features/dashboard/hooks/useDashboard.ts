"use client";

import { useQuery } from "@tanstack/react-query";
import { dashboardService } from "../services/dashboardService";

export const dashboardKeys = {
  root: () => ["me", "dashboard"] as const,
};

export function useDashboard() {
  return useQuery({
    queryKey: dashboardKeys.root(),
    queryFn: dashboardService.get,
    staleTime: 30_000,
  });
}
