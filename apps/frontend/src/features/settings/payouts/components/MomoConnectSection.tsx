"use client";

import { useState } from "react";
import { CheckCircle2, ExternalLink, Loader2, Smartphone, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  SettingsCard,
  SettingsField,
} from "@/features/settings/components/SettingsPrimitives";
import {
  useConnectMomo,
  useDisconnectMomo,
  usePayoutStatus,
} from "../hooks/usePayouts";

/**
 * Per-author MoMo Business connect — author registers with MoMo Business
 * out-of-band (Vietnamese business documents required) and pastes the
 * resulting credentials here so VND checkouts route to *their* MoMo
 * balance instead of the platform's.
 *
 * If the author skips this, VND sales fall back to platform-collects
 * (platform pays them out manually). The card flips between connected
 * + disconnected views and never shows raw secrets back to the user.
 */
export function MomoConnectSection() {
  const { data: status } = usePayoutStatus();
  const connect = useConnectMomo();
  const disconnect = useDisconnectMomo();

  const [partnerCode, setPartnerCode] = useState("");
  const [accessKey, setAccessKey] = useState("");
  const [secretKey, setSecretKey] = useState("");
  const [editing, setEditing] = useState(false);

  const connected = !!status?.momo_connected;
  const showForm = !connected || editing;

  const ready = partnerCode.trim() && accessKey.trim() && secretKey.trim();

  const handleConnect = (e: React.FormEvent) => {
    e.preventDefault();
    if (!ready) return;
    connect.mutate(
      {
        partner_code: partnerCode.trim(),
        access_key: accessKey.trim(),
        secret_key: secretKey.trim(),
      },
      {
        onSuccess: () => {
          toast.success("MoMo merchant connected");
          setPartnerCode("");
          setAccessKey("");
          setSecretKey("");
          setEditing(false);
        },
        onError: (err) =>
          toast.error(err instanceof Error ? err.message : "Couldn't save credentials"),
      },
    );
  };

  const handleDisconnect = () => {
    if (
      !window.confirm(
        "Disconnect MoMo? VND checkouts on your templates will fall back to platform-collects.",
      )
    )
      return;
    disconnect.mutate(undefined, {
      onSuccess: () => toast.success("MoMo disconnected — falling back to platform-collects"),
    });
  };

  return (
    <SettingsCard
      title="MoMo (VND payments)"
      description="Optional — connect your own MoMo Business merchant account so VND sales settle directly to you. Skip to use platform-collects (we settle you manually)."
      action={
        connected && !editing ? (
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setEditing(true)}
              disabled={disconnect.isPending}
            >
              Replace
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleDisconnect}
              disabled={disconnect.isPending}
              className="gap-1.5 text-destructive hover:text-destructive"
            >
              {disconnect.isPending ? (
                <Loader2 className="h-3 w-3 animate-spin" />
              ) : (
                <Trash2 className="h-3 w-3" />
              )}
              Disconnect
            </Button>
          </div>
        ) : null
      }
    >
      {connected && !editing ? (
        <div className="flex items-start gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-emerald-500/10">
            <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium text-emerald-700 dark:text-emerald-300">
              MoMo merchant connected
            </p>
            <p className="mt-0.5 text-[11px] text-muted-foreground">
              Partner code{" "}
              <code className="rounded bg-muted px-1 py-0.5 font-mono">
                {status?.momo_partner_code}
              </code>
              . Buyer payments on your VND templates settle directly to your MoMo account
              on its standard payout schedule.
            </p>
          </div>
        </div>
      ) : (
        <form onSubmit={handleConnect} className="space-y-4">
          <div className="flex items-start gap-3 rounded-md border border-amber-500/30 bg-amber-500/5 p-3 text-[11px] text-amber-700 dark:text-amber-300">
            <Smartphone className="mt-0.5 h-3.5 w-3.5 shrink-0" />
            <div>
              <p className="font-medium">You need a MoMo Business merchant account first.</p>
              <p className="mt-0.5 text-amber-700/80 dark:text-amber-300/80">
                Register at{" "}
                <a
                  href="https://business.momo.vn"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-0.5 underline"
                >
                  business.momo.vn
                  <ExternalLink className="h-2.5 w-2.5" />
                </a>{" "}
                with Vietnamese business documents. Approval takes a few business days.
                Then copy the three credentials from your dashboard below.
              </p>
            </div>
          </div>

          <SettingsField label="Partner code" htmlFor="momo-partner">
            <Input
              id="momo-partner"
              value={partnerCode}
              onChange={(e) => setPartnerCode(e.target.value)}
              placeholder="MOMOXXXX"
              required
            />
          </SettingsField>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <SettingsField label="Access key" htmlFor="momo-access">
              <Input
                id="momo-access"
                value={accessKey}
                onChange={(e) => setAccessKey(e.target.value)}
                required
              />
            </SettingsField>
            <SettingsField
              label="Secret key"
              hint="Encrypted at rest. We never display it back."
              htmlFor="momo-secret"
            >
              <Input
                id="momo-secret"
                type="password"
                value={secretKey}
                onChange={(e) => setSecretKey(e.target.value)}
                required
              />
            </SettingsField>
          </div>

          <div className="flex justify-end gap-2">
            {editing && (
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => {
                  setEditing(false);
                  setPartnerCode("");
                  setAccessKey("");
                  setSecretKey("");
                }}
                disabled={connect.isPending}
              >
                Cancel
              </Button>
            )}
            <Button
              type="submit"
              size="sm"
              disabled={!ready || connect.isPending}
              className="gap-1.5"
            >
              {connect.isPending ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <CheckCircle2 className="h-3.5 w-3.5" />
              )}
              {editing ? "Save new credentials" : "Connect MoMo"}
            </Button>
          </div>
        </form>
      )}
    </SettingsCard>
  );
}
