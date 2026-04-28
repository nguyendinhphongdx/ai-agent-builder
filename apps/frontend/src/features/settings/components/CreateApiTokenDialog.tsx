"use client";

import { useMemo, useState } from "react";
import { Check, Copy, Loader2, ShieldAlert } from "lucide-react";
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
import { cn } from "@/lib/utils";
import {
  PERSONAL_TOKEN_SCOPES,
  personalTokenService,
  type PersonalTokenCreated,
} from "@/lib/api/personalTokenService";

interface CreateApiTokenDialogProps {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  onCreated: () => void;
}

export function CreateApiTokenDialog(props: CreateApiTokenDialogProps) {
  // Render body only when open so state resets on remount.
  return (
    <Dialog open={props.open} onOpenChange={props.onOpenChange}>
      {props.open && <Body {...props} />}
    </Dialog>
  );
}

function Body({ onOpenChange, onCreated }: CreateApiTokenDialogProps) {
  const [name, setName] = useState("");
  const [scopes, setScopes] = useState<Set<string>>(
    () => new Set(["agents:read", "agents:chat"]),
  );
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // After create, we hold the plaintext + show "copy once" view.
  const [created, setCreated] = useState<PersonalTokenCreated | null>(null);
  const [copied, setCopied] = useState(false);

  const groupedScopes = useMemo(() => {
    const groups = new Map<string, typeof PERSONAL_TOKEN_SCOPES[number][]>();
    for (const s of PERSONAL_TOKEN_SCOPES) {
      const arr = groups.get(s.group) ?? [];
      arr.push(s);
      groups.set(s.group, arr);
    }
    return Array.from(groups.entries());
  }, []);

  const toggleScope = (value: string) => {
    setScopes((prev) => {
      const next = new Set(prev);
      if (next.has(value)) next.delete(value);
      else next.add(value);
      return next;
    });
  };

  const handleSubmit = async () => {
    if (!name.trim() || scopes.size === 0) return;
    setSubmitting(true);
    setError(null);
    try {
      const result = await personalTokenService.create({
        name: name.trim(),
        scopes: Array.from(scopes),
      });
      setCreated(result);
      onCreated();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create token");
    } finally {
      setSubmitting(false);
    }
  };

  const handleCopy = async () => {
    if (!created) return;
    await navigator.clipboard.writeText(created.plaintext);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // ── Step 2: token created — show plaintext ONCE ─────────────────
  if (created) {
    return (
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Token created</DialogTitle>
          <DialogDescription className="text-xs">
            Copy now — bạn sẽ không thấy lại giá trị này. Nếu mất, revoke và tạo cái mới.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3 py-2">
          <div className="flex items-start gap-2 rounded-md border border-amber-500/30 bg-amber-500/5 p-3 text-xs">
            <ShieldAlert className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-600" />
            <p className="text-amber-700 dark:text-amber-400">
              Đây là lần duy nhất plaintext token được hiển thị. Hệ thống chỉ lưu hash.
            </p>
          </div>

          <div className="space-y-1.5">
            <Label className="text-xs">Token</Label>
            <div className="flex items-center gap-2">
              <code className="flex-1 overflow-x-auto rounded-md border border-border bg-muted/50 px-3 py-2 font-mono text-xs">
                {created.plaintext}
              </code>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={handleCopy}
                className="shrink-0 gap-1.5"
              >
                {copied ? (
                  <>
                    <Check className="h-3.5 w-3.5" />
                    Copied
                  </>
                ) : (
                  <>
                    <Copy className="h-3.5 w-3.5" />
                    Copy
                  </>
                )}
              </Button>
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button size="sm" onClick={() => onOpenChange(false)}>
            Done
          </Button>
        </DialogFooter>
      </DialogContent>
    );
  }

  // ── Step 1: form ─────────────────────────────────────────────────
  return (
    <DialogContent className="sm:max-w-lg">
      <DialogHeader>
        <DialogTitle>Create API token</DialogTitle>
        <DialogDescription className="text-xs">
          Tokens cho phép app/script bên ngoài gọi API thay mặt bạn.
        </DialogDescription>
      </DialogHeader>

      <div className="space-y-4 py-1">
        <div className="space-y-1.5">
          <Label htmlFor="tk-name" className="text-xs">
            Name <span className="text-destructive">*</span>
          </Label>
          <Input
            id="tk-name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Zapier integration"
            className="h-9 text-sm"
            autoFocus
          />
        </div>

        <div className="space-y-2">
          <Label className="text-xs">
            Scopes <span className="text-destructive">*</span>
          </Label>
          <div className="space-y-3 rounded-lg border border-border bg-muted/30 p-3">
            {groupedScopes.map(([group, items]) => (
              <div key={group}>
                <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                  {group}
                </p>
                <div className="space-y-1">
                  {items.map((s) => (
                    <label
                      key={s.value}
                      className="flex cursor-pointer items-center gap-2 rounded-md px-1.5 py-1 text-xs hover:bg-accent/50"
                    >
                      <input
                        type="checkbox"
                        checked={scopes.has(s.value)}
                        onChange={() => toggleScope(s.value)}
                        className="h-3.5 w-3.5 rounded border-border"
                      />
                      <span className="flex-1">{s.label}</span>
                      <code className="font-mono text-[10px] text-muted-foreground">
                        {s.value}
                      </code>
                    </label>
                  ))}
                </div>
              </div>
            ))}
          </div>
          <p className="text-[10px] text-muted-foreground">
            Chỉ tick những scope thật sự cần — ít quyền hơn = an toàn hơn nếu token leak.
          </p>
        </div>

        {error && <p className="text-xs text-destructive">{error}</p>}
      </div>

      <DialogFooter>
        <Button variant="ghost" size="sm" onClick={() => onOpenChange(false)}>
          Cancel
        </Button>
        <Button
          size="sm"
          disabled={!name.trim() || scopes.size === 0 || submitting}
          onClick={handleSubmit}
          className={cn(submitting && "opacity-70")}
        >
          {submitting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : "Create token"}
        </Button>
      </DialogFooter>
    </DialogContent>
  );
}
