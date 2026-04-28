"use client";

import { useEffect, useMemo, useState, useCallback } from "react";
import Link from "next/link";
import { AlertTriangle, CheckCircle2, ChevronDown, Loader2, Plus } from "lucide-react";
import { Button, buttonVariants } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";
import {
  personalTokenService,
  type PersonalToken,
} from "@/lib/api/personalTokenService";
import { CreateApiTokenDialog } from "@/features/settings/components/CreateApiTokenDialog";

interface TokenPickerProps {
  /** Scopes the chosen token MUST have for the integration to work. */
  requiredScopes: string[];
  /** Currently selected token id. ``null`` until user picks. */
  value: string | null;
  onChange: (tokenId: string | null) => void;
  /** Inline label shown above the picker. */
  label?: string;
}

function isActive(t: PersonalToken): boolean {
  if (t.revoked_at) return false;
  if (t.expires_at && new Date(t.expires_at) <= new Date()) return false;
  return true;
}

function hasAllScopes(t: PersonalToken, required: string[]): boolean {
  return required.every((s) => t.scopes.includes(s));
}

export function TokenPicker({
  requiredScopes,
  value,
  onChange,
  label = "Choose a token",
}: TokenPickerProps) {
  const [tokens, setTokens] = useState<PersonalToken[]>([]);
  const [loading, setLoading] = useState(true);
  const [createOpen, setCreateOpen] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setTokens(await personalTokenService.list());
    } catch {
      setTokens([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const selected = useMemo(
    () => tokens.find((t) => t.id === value) ?? null,
    [tokens, value],
  );

  const eligible = useMemo(
    () => tokens.filter((t) => isActive(t) && hasAllScopes(t, requiredScopes)),
    [tokens, requiredScopes],
  );

  // Auto-select if user has exactly 1 eligible token and none picked yet.
  useEffect(() => {
    if (!value && eligible.length === 1) {
      onChange(eligible[0].id);
    }
  }, [eligible, value, onChange]);

  const missingScopes = selected
    ? requiredScopes.filter((s) => !selected.scopes.includes(s))
    : requiredScopes;

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <label className="text-xs font-medium">{label}</label>
        <span className="text-[10px] text-muted-foreground">
          Required: {requiredScopes.map((s) => (
            <code
              key={s}
              className="ml-1 rounded bg-muted px-1 py-0.5 font-mono text-[10px]"
            >
              {s}
            </code>
          ))}
        </span>
      </div>

      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="outline"
            className="h-10 w-full justify-between gap-2 text-xs"
            disabled={loading}
          >
            {loading ? (
              <span className="flex items-center gap-2 text-muted-foreground">
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                Loading tokens…
              </span>
            ) : selected ? (
              <span className="flex items-center gap-2">
                <span className="font-medium">{selected.name}</span>
                <code className="font-mono text-[10px] text-muted-foreground">
                  {selected.key_prefix}•••
                </code>
              </span>
            ) : (
              <span className="text-muted-foreground">— Select token —</span>
            )}
            <ChevronDown className="h-3.5 w-3.5 opacity-60" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="w-[--radix-dropdown-menu-trigger-width]">
          {tokens.length === 0 ? (
            <div className="px-2 py-3 text-center text-[11px] text-muted-foreground">
              Bạn chưa có token. Tạo token đầu tiên bên dưới.
            </div>
          ) : (
            tokens.map((t) => {
              const ok = isActive(t) && hasAllScopes(t, requiredScopes);
              return (
                <DropdownMenuItem
                  key={t.id}
                  disabled={!ok}
                  onClick={() => onChange(t.id)}
                  className="flex flex-col items-start gap-0.5 py-2 text-xs"
                >
                  <div className="flex w-full items-center gap-2">
                    <span className="flex-1 truncate font-medium">{t.name}</span>
                    <code className="font-mono text-[10px] text-muted-foreground">
                      {t.key_prefix}•••
                    </code>
                  </div>
                  <div className="text-[10px] text-muted-foreground">
                    {!isActive(t) ? (
                      <Badge variant="outline" className="px-1 py-0 text-[9px]">
                        {t.revoked_at ? "Revoked" : "Expired"}
                      </Badge>
                    ) : !hasAllScopes(t, requiredScopes) ? (
                      <span className="text-amber-600 dark:text-amber-400">
                        Missing scopes
                      </span>
                    ) : (
                      <span className="text-emerald-600 dark:text-emerald-400">
                        Ready
                      </span>
                    )}
                  </div>
                </DropdownMenuItem>
              );
            })
          )}
          <DropdownMenuSeparator />
          <DropdownMenuItem onClick={() => setCreateOpen(true)} className="gap-2 text-xs">
            <Plus className="h-3 w-3" />
            Create new token
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      {/* Status footer — green if ready, amber warning otherwise */}
      {selected ? (
        missingScopes.length === 0 ? (
          <p className="flex items-center gap-1.5 text-[11px] text-emerald-600 dark:text-emerald-400">
            <CheckCircle2 className="h-3 w-3" />
            Token đủ scope, sẵn sàng dùng.
          </p>
        ) : (
          <div
            className={cn(
              "flex items-start gap-2 rounded-md border px-3 py-2",
              "border-amber-500/30 bg-amber-500/5",
            )}
          >
            <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-600" />
            <div className="text-[11px]">
              <p className="font-medium text-amber-700 dark:text-amber-400">
                Token này thiếu scope cần thiết
              </p>
              <p className="mt-0.5 text-muted-foreground">
                Thiếu: {missingScopes.map((s) => (
                  <code key={s} className="ml-1 font-mono">{s}</code>
                ))}
                . Tạo token mới với đủ scope, hoặc revoke + tạo lại.
              </p>
              <Link
                href="/settings"
                className={cn(
                  buttonVariants({ size: "sm", variant: "outline" }),
                  "mt-2 h-6 gap-1.5 text-[10px]",
                )}
              >
                Manage tokens
              </Link>
            </div>
          </div>
        )
      ) : !loading && eligible.length === 0 && tokens.length > 0 ? (
        <p className="text-[11px] text-amber-600 dark:text-amber-400">
          Không có token nào đủ scope cho integration này. Tạo token mới.
        </p>
      ) : null}

      <CreateApiTokenDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        onCreated={() => {
          load();
        }}
      />
    </div>
  );
}
