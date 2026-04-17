"use client";

import { Plus } from "lucide-react";

interface HandlePlusProps {
  onClick: () => void;
}

export function HandlePlus({ onClick }: HandlePlusProps) {
  return (
    <button
      onClick={(e) => {
        e.stopPropagation();
        onClick();
      }}
      className="absolute top-1/2 -translate-y-1/2 -right-8 flex h-5 w-5 items-center justify-center rounded-md border border-border bg-background text-muted-foreground shadow-sm transition-colors hover:bg-accent hover:text-foreground hover:border-primary"
    >
      <Plus className="h-3 w-3" />
    </button>
  );
}
