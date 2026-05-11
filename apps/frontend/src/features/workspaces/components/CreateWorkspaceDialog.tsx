"use client";

import { useState } from "react";
import { Loader2 } from "lucide-react";
import { useRouter } from "next/navigation";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useCreateWorkspace } from "../hooks/useWorkspaces";

interface Props {
  open: boolean;
  onOpenChange: (v: boolean) => void;
}

export function CreateWorkspaceDialog({ open, onOpenChange }: Props) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      {open && <Body onOpenChange={onOpenChange} />}
    </Dialog>
  );
}

function Body({ onOpenChange }: { onOpenChange: (v: boolean) => void }) {
  const router = useRouter();
  const create = useCreateWorkspace();
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    const trimmed = name.trim();
    if (!trimmed) {
      setError("Tên không được để trống.");
      return;
    }
    try {
      await create.mutateAsync({ name: trimmed });
      onOpenChange(false);
      // Nudge the user toward the new workspace's settings page so
      // they can invite teammates right away.
      router.push("/settings/workspace");
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Tạo workspace thất bại";
      setError(msg);
    }
  };

  return (
    <DialogContent className="sm:max-w-md">
      <DialogHeader>
        <DialogTitle>Create workspace</DialogTitle>
        <DialogDescription>
          Workspace mới sẽ thuộc 1 organization riêng — bạn là owner mặc định.
        </DialogDescription>
      </DialogHeader>

      <div className="space-y-3 py-2">
        <div className="space-y-1">
          <Label htmlFor="ws-name" className="text-xs">
            Name
          </Label>
          <Input
            id="ws-name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Acme Inc"
            autoFocus
            maxLength={255}
          />
        </div>
        {error && (
          <p className="text-[11px] text-destructive">{error}</p>
        )}
      </div>

      <DialogFooter>
        <Button variant="ghost" size="sm" onClick={() => onOpenChange(false)}>
          Cancel
        </Button>
        <Button size="sm" onClick={submit} disabled={create.isPending}>
          {create.isPending ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            "Create"
          )}
        </Button>
      </DialogFooter>
    </DialogContent>
  );
}
