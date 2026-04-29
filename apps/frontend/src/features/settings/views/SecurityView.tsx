"use client";

import { useState } from "react";
import { CheckCircle2, Loader2, Mail, ShieldCheck } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  useAuth,
  useChangePassword,
  useConfirmEmailChange,
  useRequestEmailChange,
} from "@/features/auth/hooks/useAuth";
import {
  SettingsCard,
  SettingsField,
  SettingsPageHeader,
  SettingsStack,
} from "../components/SettingsPrimitives";

/**
 * Account security — password + email change. OAuth-only users
 * (no password set) see read-only states with a hint to use
 * forgot-password to provision one first.
 */
export function SecurityView() {
  const { user } = useAuth();
  if (!user) {
    return (
      <div className="flex h-32 items-center justify-center">
        <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div>
      <SettingsPageHeader
        title="Security"
        description="Change your password or move the account to a different email."
      />

      <SettingsStack>
        <PasswordSection />
        <EmailSection />
      </SettingsStack>
    </div>
  );
}

// ─── Password ───────────────────────────────────────────────────────

function PasswordSection() {
  const change = useChangePassword();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");

  const errors = (() => {
    if (next && next.length < 8) return "New password must be ≥ 8 characters";
    if (next && confirm && next !== confirm) return "Passwords don't match";
    return null;
  })();

  const ready = !errors && current && next && next === confirm;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!ready) return;
    change.mutate(
      { current_password: current, new_password: next },
      {
        onSuccess: () => {
          toast.success("Password updated. Other sessions were signed out.");
          setCurrent("");
          setNext("");
          setConfirm("");
        },
        onError: (err) => {
          // Backend returns 400 with `detail` on bad input; surface it
          // unchanged — wrong-password is the most common case.
          const msg =
            err instanceof Error
              ? err.message
              : "Couldn't change password — try again";
          toast.error(msg);
        },
      },
    );
  };

  return (
    <SettingsCard
      title="Password"
      description="Other active sessions will be signed out automatically."
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        <SettingsField label="Current password" htmlFor="pw-current">
          <Input
            id="pw-current"
            type="password"
            autoComplete="current-password"
            value={current}
            onChange={(e) => setCurrent(e.target.value)}
            required
          />
        </SettingsField>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <SettingsField label="New password" htmlFor="pw-new">
            <Input
              id="pw-new"
              type="password"
              autoComplete="new-password"
              value={next}
              onChange={(e) => setNext(e.target.value)}
              minLength={8}
              required
            />
          </SettingsField>
          <SettingsField label="Confirm" htmlFor="pw-confirm">
            <Input
              id="pw-confirm"
              type="password"
              autoComplete="new-password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              minLength={8}
              required
            />
          </SettingsField>
        </div>

        {errors && <p className="text-[11px] text-destructive">{errors}</p>}

        <div className="flex justify-end">
          <Button type="submit" disabled={!ready || change.isPending} className="gap-1.5">
            {change.isPending ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <ShieldCheck className="h-3.5 w-3.5" />
            )}
            Update password
          </Button>
        </div>
      </form>
    </SettingsCard>
  );
}

// ─── Email ──────────────────────────────────────────────────────────

function EmailSection() {
  const { user } = useAuth();
  const request = useRequestEmailChange();
  const confirm = useConfirmEmailChange();

  // Two-step UI: form to request → form to enter the code mailed to the
  // new address. `pending` holds the masked target between steps.
  const [pending, setPending] = useState<string | null>(null);
  const [newEmail, setNewEmail] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");

  const handleRequest = (e: React.FormEvent) => {
    e.preventDefault();
    request.mutate(
      { new_email: newEmail, current_password: password },
      {
        onSuccess: (res) => {
          setPending(res.to);
          setPassword("");
          toast.success(`Verification code sent to ${res.to}`);
        },
        onError: (err) => {
          const msg = err instanceof Error ? err.message : "Couldn't send code";
          toast.error(msg);
        },
      },
    );
  };

  const handleConfirm = (e: React.FormEvent) => {
    e.preventDefault();
    confirm.mutate(
      { code },
      {
        onSuccess: () => {
          toast.success("Email updated. Other sessions were signed out.");
          setPending(null);
          setNewEmail("");
          setCode("");
        },
        onError: (err) => {
          const msg = err instanceof Error ? err.message : "Code didn't verify";
          toast.error(msg);
        },
      },
    );
  };

  const handleCancel = () => {
    setPending(null);
    setNewEmail("");
    setCode("");
  };

  return (
    <SettingsCard
      title="Email"
      description={`Currently ${user?.email ?? "—"}. Changing it logs out other sessions.`}
    >
      {pending ? (
        <form onSubmit={handleConfirm} className="space-y-4">
          <div className="flex items-start gap-2 rounded-md border border-emerald-500/30 bg-emerald-500/5 p-3 text-[11px] text-emerald-700 dark:text-emerald-300">
            <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0" />
            <div>
              <p className="font-medium">Code sent to {pending}</p>
              <p className="mt-0.5 text-emerald-700/80 dark:text-emerald-300/80">
                Open that inbox and paste the 6-digit code below. The code
                expires in ~15 minutes.
              </p>
            </div>
          </div>

          <SettingsField label="Verification code" htmlFor="em-code">
            <Input
              id="em-code"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              inputMode="numeric"
              pattern="[0-9]{4,12}"
              required
              autoFocus
            />
          </SettingsField>

          <div className="flex justify-end gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleCancel}
              disabled={confirm.isPending}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              size="sm"
              disabled={!code || confirm.isPending}
              className="gap-1.5"
            >
              {confirm.isPending ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Mail className="h-3.5 w-3.5" />
              )}
              Confirm
            </Button>
          </div>
        </form>
      ) : (
        <form onSubmit={handleRequest} className="space-y-4">
          <SettingsField label="New email" htmlFor="em-new">
            <Input
              id="em-new"
              type="email"
              autoComplete="email"
              value={newEmail}
              onChange={(e) => setNewEmail(e.target.value)}
              required
            />
          </SettingsField>

          <SettingsField
            label="Current password"
            hint="Required so a hijacked session can't silently move the account."
            htmlFor="em-password"
          >
            <Input
              id="em-password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </SettingsField>

          <div className="flex justify-end">
            <Button
              type="submit"
              disabled={!newEmail || !password || request.isPending}
              className="gap-1.5"
            >
              {request.isPending ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Mail className="h-3.5 w-3.5" />
              )}
              Send verification code
            </Button>
          </div>
        </form>
      )}
    </SettingsCard>
  );
}
