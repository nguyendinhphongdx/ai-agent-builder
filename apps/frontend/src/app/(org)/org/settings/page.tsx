"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Loader2, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { organizationsService } from "@/lib/api/organizationsService";
import { sessionService } from "@/lib/api/sessionService";
import { useActiveOrg } from "@/features/organizations/components/OrgLayout";
import {
  SettingsCard,
  SettingsStack,
} from "@/features/settings/components/SettingsPrimitives";

/**
 * Org → Settings tab. Org name, billing email, danger-zone delete.
 *
 * The slug is read-only here on purpose. URLs today don't include
 * the slug, but it's still used in audit logs / outbound webhook
 * payloads / share-link generation — renaming silently breaks
 * those. Display name is the editable surface; slug is forever.
 */
export default function OrgSettingsPage() {
  const router = useRouter();
  const qc = useQueryClient();
  const { org, isLoading } = useActiveOrg();

  const [name, setName] = useState("");
  const [billingEmail, setBillingEmail] = useState("");

  // Re-seed local form state when the org refetches (e.g. after a save).
  useEffect(() => {
    if (org) {
      setName(org.name);
      setBillingEmail(org.billing_email ?? "");
    }
  }, [org]);

  const update = useMutation({
    mutationFn: () =>
      organizationsService.update(org!.id, {
        name: name.trim(),
        billing_email: billingEmail.trim() || null,
      }),
    onSuccess: () => {
      toast.success("Organization updated");
      qc.invalidateQueries({ queryKey: ["organizations"] });
    },
    onError: (e) => toast.error(extractMsg(e)),
  });

  const del = useMutation({
    mutationFn: () => organizationsService.delete(org!.id),
    onSuccess: async () => {
      toast.success("Organization deleted");
      // Cookie now points at a workspace that no longer exists.
      // Drop to a user-scoped token + bounce to /org so the FE can
      // pick another org (or render the empty state).
      try {
        await sessionService.exit();
      } catch {
        // ignored — even if exit fails, /org route group's guard
        // will surface the right next state.
      }
      qc.invalidateQueries();
      router.replace("/org");
    },
    onError: (e) => toast.error(extractMsg(e)),
  });

  if (isLoading || !org) {
    return <Spinner />;
  }

  const dirty =
    name.trim() !== org.name || (billingEmail.trim() || null) !== org.billing_email;
  const canEdit = org.role === "owner" || org.role === "admin";
  const canDelete = org.role === "owner";

  return (
    <div className="mx-auto max-w-3xl px-6 py-10 lg:px-8">
      <header className="border-b border-border pb-6">
        <h1 className="text-2xl font-bold tracking-tight">Organization settings</h1>
        <p className="mt-1 text-xs text-muted-foreground">
          Tên + email nhận hóa đơn. Slug <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-[10px]">{org.slug}</code> không đổi được — đổi sẽ phá link đã chia sẻ.
        </p>
      </header>

      <SettingsStack>
        <SettingsCard
          title="General"
          description="Tên hiển thị + email nhận hóa đơn Stripe."
        >
          <div className="space-y-4 p-5">
            <div className="space-y-1">
              <Label htmlFor="org-name" className="text-[11px]">Name</Label>
              <Input
                id="org-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                disabled={!canEdit}
                maxLength={255}
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="org-billing-email" className="text-[11px]">
                Billing email
              </Label>
              <Input
                id="org-billing-email"
                type="email"
                value={billingEmail}
                onChange={(e) => setBillingEmail(e.target.value)}
                disabled={!canEdit}
                placeholder={org.role === "owner" ? "billing@yourcompany.com" : ""}
              />
              <p className="text-[10px] text-muted-foreground">
                Stripe gửi invoice tới đây. Bỏ trống = dùng email owner.
              </p>
            </div>
            <div className="flex justify-end">
              <Button
                size="sm"
                disabled={!dirty || !canEdit || update.isPending}
                onClick={() => update.mutate()}
              >
                {update.isPending ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  "Save"
                )}
              </Button>
            </div>
            {!canEdit && (
              <p className="text-[10px] text-muted-foreground">
                Bạn là <strong>{org.role}</strong> — chỉ owner/admin sửa được.
              </p>
            )}
          </div>
        </SettingsCard>

        {canDelete && (
          <SettingsCard
            title="Danger zone"
            description="Xóa org sẽ xóa cascade: tất cả workspaces, agents, KB, conversations. Sub Stripe (nếu có) bị cancel. Không thể undo."
            className="border-rose-500/40 bg-rose-500/5"
          >
            <DangerZone
              orgName={org.name}
              onDelete={() => del.mutate()}
              loading={del.isPending}
            />
          </SettingsCard>
        )}
      </SettingsStack>
    </div>
  );
}

function DangerZone({
  orgName,
  onDelete,
  loading,
}: {
  orgName: string;
  onDelete: () => void;
  loading: boolean;
}) {
  const [confirm, setConfirm] = useState("");
  const canDelete = confirm === orgName;
  return (
    <div className="space-y-3 p-5">
      <div className="space-y-1">
        <Label htmlFor="org-delete-confirm" className="text-[11px]">
          Type the org name to confirm:{" "}
          <code className="rounded bg-muted px-1 font-mono">{orgName}</code>
        </Label>
        <Input
          id="org-delete-confirm"
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
          placeholder={orgName}
        />
      </div>
      <Button
        size="sm"
        variant="destructive"
        disabled={!canDelete || loading}
        onClick={onDelete}
      >
        {loading ? (
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
        ) : (
          <Trash2 className="mr-1.5 h-3.5 w-3.5" />
        )}
        Delete organization
      </Button>
    </div>
  );
}

function Spinner() {
  return (
    <div className="flex h-32 items-center justify-center">
      <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
    </div>
  );
}

function extractMsg(err: unknown): string {
  const anyErr = err as {
    response?: { data?: { detail?: string | object } };
    message?: string;
  };
  const detail = anyErr?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (detail && typeof detail === "object") return JSON.stringify(detail);
  return anyErr?.message ?? "Request failed";
}
