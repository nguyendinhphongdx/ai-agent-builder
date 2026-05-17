"use client";

import { useQuery } from "@tanstack/react-query";
import { organizationsService } from "@/lib/api/organizationsService";

/**
 * Returns whether the current user is a member of the system org and
 * which role they hold. Lets ``/system/*`` pages gate render + the
 * sidebar decide whether to surface the "Platform admin" link.
 *
 * Cheap — reuses the same ``GET /organizations`` cache the org
 * switcher already populates.
 */
export function useSystemAccess() {
  const q = useQuery({
    queryKey: ["organizations"],
    queryFn: () => organizationsService.list(),
    staleTime: 60_000,
  });
  const systemOrg = q.data?.find((o) => o.is_system) ?? null;
  const role = systemOrg?.role ?? null;
  return {
    isLoading: q.isLoading,
    isMember: !!systemOrg,
    // Owner/admin can mutate (/api/system/* writes); editor/viewer
    // can read. Distinguish for menu/button gating.
    canWrite: role === "owner" || role === "admin",
    role,
    systemOrg,
  };
}
