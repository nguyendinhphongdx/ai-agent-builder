"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ChevronDown, ChevronRight, Loader2, ShieldCheck } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { permissionsService } from "@/lib/api/permissionsService";

/**
 * Read-only permission inspector. Shows each built-in role and the
 * permission set it grants — drops in on the Workspace settings page
 * so users can answer "what can I/they do?" without diving into docs.
 *
 * Custom role authoring lives on its own page (Block 3 follow-up).
 */
export function RoleInspector() {
  const { data, isLoading } = useQuery({
    queryKey: ["permissions-catalogue"],
    queryFn: permissionsService.catalogue,
    // Catalogue is static for the page lifetime.
    staleTime: 5 * 60 * 1000,
  });

  if (isLoading || !data) {
    return (
      <div className="flex h-24 items-center justify-center">
        <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const roles = Object.entries(data.builtin_roles);

  return (
    <div className="space-y-2">
      <p className="text-[11px] text-muted-foreground">
        These are the permissions each built-in role grants. Custom roles
        (Pro plan) override this with any subset of the catalogue.
      </p>
      {roles.map(([role, perms]) => (
        <RoleRow key={role} role={role} permissions={perms} />
      ))}
    </div>
  );
}

function RoleRow({
  role,
  permissions,
}: {
  role: string;
  permissions: string[];
}) {
  const [open, setOpen] = useState(role === "owner");
  const grouped = useMemo(() => groupByDomain(permissions), [permissions]);

  return (
    <div className="rounded-md border border-border bg-card/60">
      <button
        type="button"
        className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs hover:bg-accent/30"
        onClick={() => setOpen((x) => !x)}
      >
        {open ? (
          <ChevronDown className="h-3 w-3 text-muted-foreground" />
        ) : (
          <ChevronRight className="h-3 w-3 text-muted-foreground" />
        )}
        <ShieldCheck
          className={cn(
            "h-3.5 w-3.5",
            role === "owner"
              ? "text-emerald-600"
              : role === "admin"
              ? "text-amber-600"
              : role === "editor"
              ? "text-sky-600"
              : "text-muted-foreground",
          )}
        />
        <span className="font-medium capitalize">{role}</span>
        <span className="ml-auto text-[10px] text-muted-foreground">
          {permissions.length} permission{permissions.length === 1 ? "" : "s"}
        </span>
      </button>
      {open && (
        <div className="space-y-2 border-t border-border px-3 py-3">
          {Object.entries(grouped).map(([domain, perms]) => (
            <div key={domain}>
              <p className="mb-1 text-[10px] uppercase tracking-wider text-muted-foreground">
                {domain}
              </p>
              <div className="flex flex-wrap gap-1">
                {perms.map((p) => (
                  <Badge
                    key={p}
                    variant="outline"
                    className="font-mono text-[10px]"
                  >
                    {p}
                  </Badge>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/** Group permissions by their dotted prefix for readable rendering. */
function groupByDomain(perms: string[]): Record<string, string[]> {
  const out: Record<string, string[]> = {};
  for (const p of perms) {
    const domain = p.split(".", 1)[0];
    (out[domain] ??= []).push(p);
  }
  // Stable ordering within each group.
  for (const k of Object.keys(out)) out[k].sort();
  return out;
}
