"use client";

import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ErrorState } from "@/components/ui/error-state";
import { extractError } from "../providers/utils";

/**
 * Shared form skeleton used by every trigger provider:
 * a two-column field grid, an error banner, then Cancel + Save.
 * Per-provider forms supply their own field set as `children`.
 */
export function TriggerFormShell({
  onSubmit,
  onCancel,
  isPending,
  error,
  children,
}: {
  onSubmit: () => void;
  onCancel: () => void;
  isPending: boolean;
  error: unknown;
  children: React.ReactNode;
}) {
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit();
      }}
      className="space-y-3"
    >
      <div className="grid grid-cols-2 gap-3">{children}</div>
      {error ? <ErrorState message={extractError(error)} /> : null}
      <div className="flex justify-end gap-2 pt-2">
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={onCancel}
        >
          Cancel
        </Button>
        <Button type="submit" size="sm" disabled={isPending}>
          {isPending && <Loader2 className="animate-spin" />}
          Save
        </Button>
      </div>
    </form>
  );
}
