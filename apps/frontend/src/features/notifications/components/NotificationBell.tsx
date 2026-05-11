"use client";

import { useState, useEffect } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { Bell, CheckCheck, ExternalLink, Loader2 } from "lucide-react";
import { useSocketEvent } from "@/features/notifications/hooks/useSocketEvent";
import { cn } from "@/lib/utils";
import {
  notificationsService,
  type Notification,
} from "@/lib/api/notificationsService";

/**
 * Bell icon in the header. Three behaviours:
 *   1. Click bell → toggle dropdown of 10 most recent notifications.
 *   2. Live badge — invalidates on WS "notification" event and on
 *      tab focus. Polling every 60s as a fallback for socket gaps.
 *   3. Click row → mark read + navigate to link_url.
 *
 * Keep the dropdown small (10 rows). The full inbox view at
 * /notifications has filters + pagination.
 */
export function NotificationBell() {
  const [open, setOpen] = useState(false);
  const qc = useQueryClient();

  const unreadQ = useQuery({
    queryKey: ["notifications-unread-count"],
    queryFn: () => notificationsService.unreadCount(),
    refetchInterval: 60_000,
    refetchOnWindowFocus: true,
  });

  const listQ = useQuery({
    queryKey: ["notifications-recent"],
    queryFn: () => notificationsService.list({ limit: 10 }),
    enabled: open,
  });

  const markReadM = useMutation({
    mutationFn: (id: string) => notificationsService.markRead(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["notifications-unread-count"] });
      qc.invalidateQueries({ queryKey: ["notifications-recent"] });
    },
  });

  const markAllM = useMutation({
    mutationFn: () => notificationsService.markAllRead(),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["notifications-unread-count"] });
      qc.invalidateQueries({ queryKey: ["notifications-recent"] });
    },
  });

  // Live push — when a new notification arrives, bump the badge +
  // refresh the dropdown if open.
  useSocketEvent("notification", () => {
    qc.invalidateQueries({ queryKey: ["notifications-unread-count"] });
    qc.invalidateQueries({ queryKey: ["notifications-recent"] });
  });

  // Close on outside click. Cheap implementation — sibling-aware
  // libraries (Floating UI etc.) would be overkill for one dropdown.
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      if (!target.closest("[data-notification-bell]")) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  const unread = unreadQ.data?.count ?? 0;

  return (
    <div className="relative" data-notification-bell>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="relative inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
        aria-label={`Notifications (${unread} unread)`}
      >
        <Bell className="h-4 w-4" />
        {unread > 0 && (
          <span className="absolute -top-0.5 -right-0.5 inline-flex h-4 min-w-4 items-center justify-center rounded-full bg-rose-500 px-1 text-[10px] font-semibold text-white">
            {unread > 99 ? "99+" : unread}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 top-full z-40 mt-2 w-80 overflow-hidden rounded-xl border border-border bg-popover shadow-lg">
          <div className="flex items-center justify-between border-b border-border px-3 py-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Notifications
            </span>
            <button
              type="button"
              onClick={() => markAllM.mutate()}
              disabled={unread === 0 || markAllM.isPending}
              className="inline-flex items-center gap-1 text-[10px] font-medium text-muted-foreground hover:text-foreground disabled:opacity-50"
            >
              <CheckCheck className="h-3 w-3" /> Mark all read
            </button>
          </div>

          <div className="max-h-96 overflow-y-auto">
            {listQ.isLoading ? (
              <div className="flex items-center justify-center p-4">
                <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
              </div>
            ) : (listQ.data ?? []).length === 0 ? (
              <p className="px-3 py-6 text-center text-xs text-muted-foreground">
                You're all caught up.
              </p>
            ) : (
              <ul className="divide-y divide-border">
                {(listQ.data ?? []).map((n) => (
                  <NotificationRow
                    key={n.id}
                    notification={n}
                    onClick={() => {
                      if (n.read_at === null) markReadM.mutate(n.id);
                      setOpen(false);
                    }}
                  />
                ))}
              </ul>
            )}
          </div>

          <div className="border-t border-border bg-muted/30 px-3 py-2 text-center">
            <Link
              href="/notifications"
              onClick={() => setOpen(false)}
              className="text-[11px] font-medium text-muted-foreground hover:text-foreground"
            >
              View all
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}

function NotificationRow({
  notification,
  onClick,
}: {
  notification: Notification;
  onClick: () => void;
}) {
  const unread = notification.read_at === null;
  const Wrapper = notification.link_url ? Link : "div";
  return (
    <li>
      <Wrapper
        href={notification.link_url ?? "#"}
        onClick={onClick}
        className={cn(
          "block cursor-pointer px-3 py-2.5 transition-colors hover:bg-accent/40",
          unread && "bg-primary/5",
        )}
      >
        <div className="flex items-start gap-2">
          {unread && (
            <span className="mt-1.5 inline-block h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
          )}
          <div className="min-w-0 flex-1">
            <div className="flex items-baseline justify-between gap-2">
              <span className="truncate text-sm font-medium">{notification.title}</span>
              <span className="shrink-0 text-[10px] text-muted-foreground">
                {formatTimeAgo(notification.created_at)}
              </span>
            </div>
            {notification.body && (
              <p className="mt-0.5 line-clamp-2 text-[11px] text-muted-foreground">
                {notification.body}
              </p>
            )}
            <span className="mt-0.5 inline-block font-mono text-[10px] uppercase tracking-wider text-muted-foreground/70">
              {notification.type}
              {notification.link_url && <ExternalLink className="ml-1 inline h-2.5 w-2.5" />}
            </span>
          </div>
        </div>
      </Wrapper>
    </li>
  );
}

function formatTimeAgo(iso: string): string {
  const then = new Date(iso).getTime();
  const now = Date.now();
  const sec = Math.max(1, Math.floor((now - then) / 1000));
  if (sec < 60) return `${sec}s`;
  const min = Math.floor(sec / 60);
  if (min < 60) return `${min}m`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr}h`;
  const days = Math.floor(hr / 24);
  if (days < 7) return `${days}d`;
  return new Date(iso).toLocaleDateString();
}
