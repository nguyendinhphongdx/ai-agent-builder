"use client";

import { useCallback, useMemo } from "react";
import { useParams } from "next/navigation";
import { useSession } from "./useWorkspaceSession";
import { useWorkspaces } from "./useWorkspaces";

/**
 * Build absolute paths scoped to the active workspace.
 *
 * Phase 2c of the Hub refactor (docs/architecture/hub-auth-refactor.md):
 * every internal navigation that lives *inside* a workspace context
 * (agents, chat, KB, workflows, tools, libraries, welcome, home)
 * needs the ``/app/{slug}/`` prefix so the URL stays under the
 * workspace route group and the slug guard in the layout doesn't
 * bounce around.
 *
 * Usage:
 *   const wp = useWorkspacePath();
 *   router.push(wp("/agents/new"));      // → /app/{slug}/agents/new
 *   <Link href={wp("/knowledge")}>…</Link>
 *
 * Slug resolution priority:
 *   1. URL param ``[ws-slug]`` — cheapest, set by Next.js routing.
 *   2. Session's ``workspace_id`` → lookup slug from the workspaces
 *      list. Covers callers rendered *outside* the workspace route
 *      group (header switcher, settings pages).
 *   3. No slug → return the input path unchanged. Graceful for the
 *      brief window before session loads; legacy (dashboard) routes
 *      handle the un-scoped path until Phase 3 deletes them.
 *
 * Non-workspace paths (``/org/*``, ``/hub`` marketplace, ``/login``)
 * are returned unchanged regardless — they have their own routing.
 */
const NON_WORKSPACE_PREFIXES = [
  "/login",
  "/register",
  "/forgot-password",
  "/reset-password",
  "/verify-email",
  "/org",
  "/hub",
  "/admin",
  "/settings",
  "/notifications",
  "/workspaces",
];

export function useWorkspacePath() {
  const params = useParams();
  const urlSlug = (params?.["ws-slug"] as string | undefined) ?? null;

  const sessionQ = useSession();
  const workspacesQ = useWorkspaces();

  const fallbackSlug = useMemo(() => {
    if (!sessionQ.data?.workspace_id || !workspacesQ.data) return null;
    return (
      workspacesQ.data.find((w) => w.id === sessionQ.data!.workspace_id)?.slug ??
      null
    );
  }, [sessionQ.data, workspacesQ.data]);

  const slug = urlSlug ?? fallbackSlug;

  return useCallback(
    (path: string): string => {
      if (!path.startsWith("/")) return path;
      if (NON_WORKSPACE_PREFIXES.some((p) => path === p || path.startsWith(p + "/"))) {
        return path;
      }
      if (!slug) return path;
      return `/app/${slug}${path}`;
    },
    [slug],
  );
}
