"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { CheckCheck, Inbox, Loader2 } from "lucide-react";
import {
  SettingsCard,
  SettingsPageHeader,
} from "@/features/settings/components/SettingsPrimitives";
import { useSocketEvent } from "@/features/notifications/hooks/useSocketEvent";
import { cn } from "@/lib/utils";
import {
  notificationsService,
  type Notification,
} from "@/lib/api/notificationsService";

const PAGE_SIZE = 25;

/**
 * Full inbox page. Toggle "unread only" filter + paginate. Click
 * row → mark read + jump to link_url. "Mark all read" up top.
 *
 * Live updates via WS — when a new "notification" event arrives
 * the query refetches so the user sees the new row without
 * reloading.
 */
export function NotificationsView() {
  const [page, setPage] = useState(0);
  const [unreadOnly, setUnreadOnly] = useState(false);
  const qc = useQueryClient();

  const listQ = useQuery({
    queryKey: ["notifications-inbox", page, unreadOnly],
    queryFn: () =>
      notificationsService.list({
        limit: PAGE_SIZE,
        offset: page * PAGE_SIZE,
        unread_only: unreadOnly,
      }),
  });

  const markReadM = useMutation({
    mutationFn: (id: string) => notificationsService.markRead(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["notifications-inbox"] });
      qc.invalidateQueries({ queryKey: ["notifications-unread-count"] });
    },
  });
  const markAllM = useMutation({
    mutationFn: () => notificationsService.markAllRead(),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["notifications-inbox"] });
      qc.invalidateQueries({ queryKey: ["notifications-unread-count"] });
    },
  });

  useSocketEvent("notification", () => {
    qc.invalidateQueries({ queryKey: ["notifications-inbox"] });
  });

  return (
    <div className="mx-auto max-w-4xl p-6">
      <SettingsPageHeader
        title="Notifications"
        description="Everything routed to your inbox — workflow runs, KB processing, team invites, payments."
        action={
          <div className="flex items-center gap-2">
            <label className="inline-flex cursor-pointer items-center gap-1.5 text-[11px] text-muted-foreground">
              <input
                type="checkbox"
                checked={unreadOnly}
                onChange={(e) => {
                  setUnreadOnly(e.target.checked);
                  setPage(0);
                }}
                className="h-3 w-3 accent-primary"
              />
              Unread only
            </label>
            <button
              type="button"
              onClick={() => markAllM.mutate()}
              disabled={markAllM.isPending}
              className="inline-flex items-center gap-1 rounded-md border border-border px-2.5 py-1 text-[11px] font-medium hover:bg-accent disabled:opacity-50"
            >
              <CheckCheck className="h-3 w-3" /> Mark all read
            </button>
          </div>
        }
      />

      <SettingsCard
        title={unreadOnly ? "Unread" : "All notifications"}
        description={
          listQ.data && listQ.data.length === PAGE_SIZE
            ? `Page ${page + 1}`
            : undefined
        }
      >
        {listQ.isLoading ? (
          <div className="flex items-center justify-center p-8">
            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
          </div>
        ) : (listQ.data ?? []).length === 0 ? (
          <div className="flex flex-col items-center gap-2 px-5 py-12 text-center text-muted-foreground">
            <Inbox className="h-8 w-8 opacity-40" />
            <p className="text-xs">
              {unreadOnly ? "No unread notifications." : "Inbox is empty."}
            </p>
          </div>
        ) : (
          <ul className="divide-y divide-border">
            {(listQ.data ?? []).map((n) => (
              <NotificationRow
                key={n.id}
                notification={n}
                onClick={() => {
                  if (n.read_at === null) markReadM.mutate(n.id);
                }}
              />
            ))}
          </ul>
        )}

        {(listQ.data?.length ?? 0) === PAGE_SIZE && (
          <div className="flex justify-between border-t border-border px-5 py-3">
            <button
              type="button"
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0}
              className="rounded-md border border-border px-2.5 py-1 text-[11px] hover:bg-accent disabled:opacity-50"
            >
              ← Previous
            </button>
            <button
              type="button"
              onClick={() => setPage((p) => p + 1)}
              className="rounded-md border border-border px-2.5 py-1 text-[11px] hover:bg-accent"
            >
              Next →
            </button>
          </div>
        )}
      </SettingsCard>
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
          "flex cursor-pointer items-start gap-3 px-5 py-3 transition-colors hover:bg-accent/40",
          unread && "bg-primary/5",
        )}
      >
        {unread && (
          <span className="mt-2 inline-block h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
        )}
        <div className="min-w-0 flex-1">
          <div className="flex items-baseline justify-between gap-2">
            <span className="text-sm font-medium">{notification.title}</span>
            <span className="shrink-0 text-[10px] text-muted-foreground">
              {new Date(notification.created_at).toLocaleString()}
            </span>
          </div>
          {notification.body && (
            <p className="mt-1 text-[12px] text-muted-foreground">{notification.body}</p>
          )}
          <span className="mt-1 inline-block font-mono text-[10px] uppercase tracking-wider text-muted-foreground/70">
            {notification.type}
          </span>
        </div>
      </Wrapper>
    </li>
  );
}
