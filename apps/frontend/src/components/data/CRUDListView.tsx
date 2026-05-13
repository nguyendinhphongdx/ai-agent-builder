"use client";

import { useState, type ReactNode } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ErrorState } from "@/components/ui/error-state";
import { cn } from "@/lib/utils";

type CRUDListViewProps<T> = {
  /** Card header copy. */
  title: string;
  description?: string;

  /** TanStack Query key for the list — used for cache + invalidation. */
  queryKey: readonly unknown[];
  /** Async loader returning the items. */
  fetcher: () => Promise<T[]>;
  /** Async deleter; the row's onDelete invokes this. */
  deleter?: (id: string) => Promise<unknown>;
  /** How to derive a stable id from each item (defaults to `item.id`). */
  getId?: (item: T) => string;

  /** Row renderer — receives the item + an onDelete callback. */
  RowComponent: React.ComponentType<{ item: T; onDelete: () => void }>;

  /** Optional create-form render prop. When set, a "+ New" button toggles it. */
  renderForm?: (api: { onCancel: () => void; onDone: () => void }) => ReactNode;
  /** Label for the "+ New" button (default: "New"). */
  newLabel?: string;

  /** Override empty-state copy. */
  emptyMessage?: string;

  /** Confirm prompt before deleting (default: native confirm). Set to `false` to skip. */
  confirmDelete?: ((item: T) => string) | false;

  className?: string;
};

/**
 * Generic list + create + delete card.
 *
 * Replaces the recurring pattern across triggers, members, tools, etc.:
 *   - card header with optional "+ New" toggle
 *   - inline create form (collapses on success, invalidates list)
 *   - loading spinner / empty copy / list of rows
 *   - per-row delete with confirm
 *
 * Owns TanStack Query setup so callers only supply: queryKey, fetcher,
 * RowComponent, and (optionally) a deleter + renderForm. The form is a
 * render prop because each provider needs different fields & state.
 *
 * Visual shape mirrors SettingsCard intentionally — both use the same
 * token-based card frame so they look identical in settings contexts.
 */
export function CRUDListView<T extends { id: string }>({
  title,
  description,
  queryKey,
  fetcher,
  deleter,
  getId = (item) => item.id,
  RowComponent,
  renderForm,
  newLabel = "New",
  emptyMessage = "Nothing here yet.",
  confirmDelete,
  className,
}: CRUDListViewProps<T>) {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);

  const listQ = useQuery<T[]>({
    queryKey: queryKey as unknown[],
    queryFn: fetcher,
  });

  const removeM = useMutation({
    mutationFn: (id: string) => {
      if (!deleter) throw new Error("CRUDListView: deleter not provided");
      return deleter(id);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKey as unknown[] }),
  });

  const handleDelete = (item: T) => {
    if (confirmDelete === false) {
      removeM.mutate(getId(item));
      return;
    }
    const msg =
      typeof confirmDelete === "function"
        ? confirmDelete(item)
        : "Delete this item?";
    if (window.confirm(msg)) removeM.mutate(getId(item));
  };

  return (
    <section
      className={cn("rounded-xl border border-border bg-card", className)}
    >
      <header className="flex items-start justify-between gap-3 border-b border-border px-5 py-3.5">
        <div className="min-w-0">
          <h2 className="text-sm font-semibold">{title}</h2>
          {description && (
            <p className="mt-0.5 text-[11px] text-muted-foreground">
              {description}
            </p>
          )}
        </div>
        {renderForm && !showForm && (
          <Button
            type="button"
            size="sm"
            onClick={() => setShowForm(true)}
            className="shrink-0"
          >
            <Plus />
            {newLabel}
          </Button>
        )}
      </header>

      {showForm && renderForm && (
        <div className="border-b border-border p-5">
          {renderForm({
            onCancel: () => setShowForm(false),
            onDone: () => {
              setShowForm(false);
              qc.invalidateQueries({ queryKey: queryKey as unknown[] });
            },
          })}
        </div>
      )}

      {listQ.isLoading ? (
        <div className="flex items-center justify-center p-6">
          <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
        </div>
      ) : listQ.isError ? (
        <div className="p-5">
          <ErrorState
            message={
              listQ.error instanceof Error
                ? listQ.error.message
                : "Failed to load"
            }
            onRetry={() => listQ.refetch()}
          />
        </div>
      ) : (listQ.data ?? []).length === 0 ? (
        <p className="px-5 py-6 text-xs text-muted-foreground">
          {emptyMessage}
        </p>
      ) : (
        <ul className="divide-y divide-border">
          {(listQ.data ?? []).map((item) => (
            <RowComponent
              key={getId(item)}
              item={item}
              onDelete={() => handleDelete(item)}
            />
          ))}
        </ul>
      )}
    </section>
  );
}
