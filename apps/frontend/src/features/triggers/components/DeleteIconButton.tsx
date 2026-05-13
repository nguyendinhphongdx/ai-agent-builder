"use client";

import { Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";

/**
 * Small icon-only delete affordance for list rows.
 * Hover uses the destructive token so it surfaces danger
 * without committing to a full destructive variant.
 */
export function DeleteIconButton({
  onClick,
  label = "Delete",
}: {
  onClick: () => void;
  label?: string;
}) {
  return (
    <Button
      type="button"
      variant="ghost"
      size="icon-xs"
      onClick={onClick}
      aria-label={label}
      className="text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
    >
      <Trash2 />
    </Button>
  );
}
