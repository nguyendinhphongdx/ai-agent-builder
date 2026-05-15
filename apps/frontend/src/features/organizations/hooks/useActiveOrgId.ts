"use client";

import { useSyncExternalStore } from "react";

/**
 * Active-org id, persisted in localStorage.
 *
 * Why a separate store (and not driven off the token) — the org is
 * **not** baked into the access_token. The token has either a user
 * scope or a workspace scope (see hub-auth-refactor.md). For a user
 * who belongs to many orgs, "which org's Hub am I looking at" is a
 * pure client choice, and the BE only needs it via the
 * ``X-Organization-Id`` header on org-scoped requests.
 *
 * We deliberately *don't* use zustand here — the only other store of
 * this shape (``useWorkspaceStore``) got deleted in Phase 3 of the
 * Hub refactor when workspace state moved into the token. Keeping
 * this hook tiny + dependency-free mirrors that simplification.
 *
 * Cleared on logout via ``clearActiveOrgId``.
 */

const STORAGE_KEY = "agentforge:current-org";
const CHANGE_EVENT = "agentforge:current-org:change";

function read(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

function write(value: string | null): void {
  if (typeof window === "undefined") return;
  try {
    if (value === null) {
      window.localStorage.removeItem(STORAGE_KEY);
    } else {
      window.localStorage.setItem(STORAGE_KEY, value);
    }
  } catch {
    // Storage may be disabled (private mode, etc.). Silent-fail —
    // the next call to read() will return null and the layout
    // falls back to orgs[0], which is the same behaviour we shipped
    // in Phase 1.
  }
  window.dispatchEvent(new Event(CHANGE_EVENT));
}

function subscribe(callback: () => void): () => void {
  if (typeof window === "undefined") return () => {};
  // ``storage`` only fires across tabs; the custom event handles
  // intra-tab updates (so the dropdown reflects setActiveOrgId calls).
  window.addEventListener("storage", callback);
  window.addEventListener(CHANGE_EVENT, callback);
  return () => {
    window.removeEventListener("storage", callback);
    window.removeEventListener(CHANGE_EVENT, callback);
  };
}

/** Reactive read — re-renders the component when the active org id
 *  changes in any tab. SSR returns ``null`` (no localStorage). */
export function useActiveOrgId(): string | null {
  return useSyncExternalStore(
    subscribe,
    read,
    () => null, // server snapshot
  );
}

/** Imperative setter. Pass ``null`` to clear. Triggers re-renders in
 *  every active hook subscriber. */
export function setActiveOrgId(orgId: string | null): void {
  write(orgId);
}

/** Convenience for the logout flow — drops the persisted choice so
 *  the next user's first sign-in lands on their default org rather
 *  than the previous user's last-active. */
export function clearActiveOrgId(): void {
  write(null);
}
