"use client";

import { useEffect, useState } from "react";
import { Copy, KeyRound, Loader2, ShieldCheck, ShieldX } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { mfaService, type MfaStatus } from "@/lib/api/mfaService";
import { SettingsCard } from "./SettingsPrimitives";

/**
 * Security tab MFA controls. State machine driven off `mfa_status`:
 *
 *   not enrolled   → "Enable MFA" button starts setup flow
 *   pending        → QR + secret + confirm code form
 *   enrolled       → backup-codes-remaining + regenerate + disable
 *
 * Backup codes are shown ONCE in a modal after enrol/regenerate.
 * No backend persistence of plaintext — the user must screenshot
 * or copy.
 */
export function MfaSection() {
  const [status, setStatus] = useState<MfaStatus | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = async () => {
    setLoading(true);
    try {
      setStatus(await mfaService.status());
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void refresh();
  }, []);

  return (
    <SettingsCard
      title="Two-factor authentication"
      description="TOTP via authenticator app. Backup codes cover lost-phone recovery."
    >
      <div className="p-5">
        {loading ? (
          <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
        ) : status?.mfa_enabled ? (
          <EnrolledState status={status} onChange={refresh} />
        ) : (
          <NotEnrolledState onEnrolled={refresh} />
        )}
      </div>
    </SettingsCard>
  );
}

/* ─── Not enrolled → setup wizard ────────────────────────────── */

function NotEnrolledState({ onEnrolled }: { onEnrolled: () => void }) {
  const [setup, setSetup] = useState<{ secret: string; uri: string } | null>(null);
  const [code, setCode] = useState("");
  const [backupCodes, setBackupCodes] = useState<string[] | null>(null);
  const [busy, setBusy] = useState(false);

  const start = async () => {
    setBusy(true);
    try {
      const res = await mfaService.setupTotp();
      setSetup({ secret: res.secret, uri: res.provisioning_uri });
    } catch (e) {
      toast.error(msg(e));
    } finally {
      setBusy(false);
    }
  };

  const verify = async () => {
    setBusy(true);
    try {
      const res = await mfaService.verifySetupTotp(code);
      setBackupCodes(res.backup_codes);
    } catch (e) {
      toast.error(msg(e));
    } finally {
      setBusy(false);
    }
  };

  if (backupCodes) {
    return <BackupCodesDisplay codes={backupCodes} onDone={onEnrolled} />;
  }

  if (!setup) {
    return (
      <div className="flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-full bg-muted">
          <ShieldX className="h-4 w-4 text-muted-foreground" />
        </div>
        <div className="flex-1">
          <p className="text-sm font-medium">MFA off</p>
          <p className="text-[11px] text-muted-foreground">
            Enable to protect against credential stuffing + add a recovery factor.
          </p>
        </div>
        <Button size="sm" onClick={start} disabled={busy}>
          {busy ? <Loader2 className="h-3 w-3 animate-spin" /> : "Enable MFA"}
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div>
        <p className="text-xs font-medium">1. Scan QR with your authenticator</p>
        <p className="mt-0.5 text-[11px] text-muted-foreground">
          Google Authenticator, 1Password, Authy — all support otpauth://.
        </p>
        <div className="mt-3 flex flex-col items-center gap-3 rounded-lg border border-border bg-muted/30 p-4">
          <QRView uri={setup.uri} />
          <div className="text-center">
            <p className="text-[10px] uppercase tracking-wider text-muted-foreground">
              Or enter manually
            </p>
            <code className="mt-1 inline-block rounded bg-muted px-2 py-1 font-mono text-xs">
              {setup.secret}
            </code>
            <Button
              variant="ghost"
              size="sm"
              className="ml-1 h-6 px-1.5"
              onClick={() => {
                navigator.clipboard.writeText(setup.secret);
                toast.success("Copied");
              }}
            >
              <Copy className="h-3 w-3" />
            </Button>
          </div>
        </div>
      </div>

      <div>
        <p className="text-xs font-medium">2. Confirm with a 6-digit code</p>
        <div className="mt-2 flex gap-2">
          <Input
            value={code}
            onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
            placeholder="000000"
            inputMode="numeric"
            maxLength={6}
            className="font-mono tracking-widest"
          />
          <Button
            size="sm"
            onClick={verify}
            disabled={busy || code.length !== 6}
          >
            {busy ? (
              <Loader2 className="h-3 w-3 animate-spin" />
            ) : (
              "Verify"
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}

function QRView({ uri }: { uri: string }) {
  // Lightweight QR using Google's chart API — no extra dep + works
  // offline-once-cached. For air-gapped deployments swap for a local
  // QR lib later.
  const src = `https://api.qrserver.com/v1/create-qr-code/?size=180x180&data=${encodeURIComponent(uri)}`;
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={src}
      alt="MFA QR code"
      width={180}
      height={180}
      className="rounded-md border border-border bg-white"
    />
  );
}

/* ─── Enrolled → status + regen + disable ────────────────────── */

function EnrolledState({
  status,
  onChange,
}: {
  status: MfaStatus;
  onChange: () => void;
}) {
  const [regenCodes, setRegenCodes] = useState<string[] | null>(null);
  const [disableCode, setDisableCode] = useState("");
  const [showDisable, setShowDisable] = useState(false);
  const [busy, setBusy] = useState(false);

  const regen = async () => {
    if (!confirm("Burn existing backup codes and mint 10 new ones?")) return;
    setBusy(true);
    try {
      const res = await mfaService.regenerateBackupCodes();
      setRegenCodes(res.backup_codes);
    } catch (e) {
      toast.error(msg(e));
    } finally {
      setBusy(false);
    }
  };

  const disable = async () => {
    setBusy(true);
    try {
      await mfaService.disable(disableCode);
      toast.success("MFA disabled");
      onChange();
    } catch (e) {
      toast.error(msg(e));
    } finally {
      setBusy(false);
    }
  };

  if (regenCodes) {
    return (
      <BackupCodesDisplay
        codes={regenCodes}
        onDone={() => {
          setRegenCodes(null);
          onChange();
        }}
      />
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-full bg-emerald-500/15">
          <ShieldCheck className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
        </div>
        <div className="flex-1">
          <p className="text-sm font-medium">MFA on</p>
          <p className="text-[11px] text-muted-foreground">
            {status.backup_codes_remaining} backup code
            {status.backup_codes_remaining === 1 ? "" : "s"} remaining
          </p>
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        <Button size="sm" variant="outline" onClick={regen} disabled={busy}>
          <KeyRound className="mr-1.5 h-3 w-3" />
          Regenerate backup codes
        </Button>
        <Button
          size="sm"
          variant="ghost"
          className="text-destructive hover:bg-destructive/10 hover:text-destructive"
          onClick={() => setShowDisable((x) => !x)}
        >
          Disable MFA
        </Button>
      </div>

      {showDisable && (
        <div className="rounded-md border border-destructive/30 bg-destructive/5 p-3">
          <Label htmlFor="disable-code" className="text-[11px]">
            Confirm with a code from your app (or backup code):
          </Label>
          <div className="mt-1 flex gap-2">
            <Input
              id="disable-code"
              value={disableCode}
              onChange={(e) => setDisableCode(e.target.value)}
              placeholder="000000 or backup code"
              className="font-mono"
            />
            <Button
              size="sm"
              variant="destructive"
              onClick={disable}
              disabled={busy || !disableCode.trim()}
            >
              Disable
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

/* ─── Backup codes display (shown once) ──────────────────────── */

function BackupCodesDisplay({
  codes,
  onDone,
}: {
  codes: string[];
  onDone: () => void;
}) {
  const text = codes.join("\n");
  return (
    <div className="space-y-3">
      <div>
        <p className="text-xs font-medium text-emerald-600 dark:text-emerald-400">
          MFA enrolled — save these backup codes
        </p>
        <p className="mt-0.5 text-[11px] text-muted-foreground">
          Each code works once. Store them somewhere safe (password manager,
          printed copy). You won't see them again.
        </p>
      </div>
      <pre className="rounded-md border border-border bg-muted/30 p-3 font-mono text-xs">
        {text}
      </pre>
      <div className="flex gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => {
            navigator.clipboard.writeText(text);
            toast.success("Copied");
          }}
        >
          <Copy className="mr-1.5 h-3 w-3" />
          Copy all
        </Button>
        <Button size="sm" onClick={onDone}>
          I've saved them
        </Button>
      </div>
    </div>
  );
}

function msg(e: unknown): string {
  if (e && typeof e === "object" && "response" in e) {
    const r = (e as { response?: { data?: { detail?: string } } }).response;
    if (r?.data?.detail) return r.data.detail;
  }
  return e instanceof Error ? e.message : "Something went wrong";
}
