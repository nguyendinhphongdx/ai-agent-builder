"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { CheckCircle2, Loader2, Mail } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { AuthLayout } from "../components/AuthLayout";
import {
  useAuth,
  useLogout,
  useResendVerification,
  useVerifyEmailConfirm,
} from "../hooks/useAuth";

const CODE_LENGTH = 6;
const COOLDOWN_SECONDS = 60;

/** Split a string into its first N digits, trimming non-numeric characters. */
function sanitise(input: string): string {
  return input.replace(/\D/g, "").slice(0, CODE_LENGTH);
}

export function VerifyEmailPendingView() {
  const router = useRouter();
  const { user } = useAuth();
  const resend = useResendVerification();
  const confirm = useVerifyEmailConfirm();
  const logout = useLogout();

  const [digits, setDigits] = useState<string[]>(
    Array.from({ length: CODE_LENGTH }, () => ""),
  );
  const inputsRef = useRef<Array<HTMLInputElement | null>>([]);
  const [cooldown, setCooldown] = useState(0);
  const [didResend, setDidResend] = useState(false);

  // Focus first empty cell on mount
  useEffect(() => {
    inputsRef.current[0]?.focus();
  }, []);

  // Cooldown tick
  useEffect(() => {
    if (cooldown <= 0) return;
    const t = setTimeout(() => setCooldown((s) => s - 1), 1000);
    return () => clearTimeout(t);
  }, [cooldown]);

  // Auto-submit as soon as all 6 digits are filled
  const code = digits.join("");
  useEffect(() => {
    if (code.length === CODE_LENGTH && !confirm.isPending) {
      confirm
        .mutateAsync({ code })
        .then(() => router.push("/org"))
        .catch(() => {
          // clear + refocus first cell so user can retry
          setDigits(Array.from({ length: CODE_LENGTH }, () => ""));
          inputsRef.current[0]?.focus();
        });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [code]);

  // Already verified (eg. via another tab) — push them into the app
  useEffect(() => {
    if (user?.is_verified) router.replace("/org");
  }, [user?.is_verified, router]);

  const handleChange = (index: number, value: string) => {
    const cleaned = sanitise(value);
    // User pasted the whole code → distribute across cells
    if (cleaned.length > 1) {
      const next = Array.from({ length: CODE_LENGTH }, (_, i) => cleaned[i] ?? "");
      setDigits(next);
      const lastFilled = Math.min(cleaned.length, CODE_LENGTH) - 1;
      inputsRef.current[Math.min(lastFilled + 1, CODE_LENGTH - 1)]?.focus();
      return;
    }
    setDigits((prev) => {
      const next = [...prev];
      next[index] = cleaned;
      return next;
    });
    if (cleaned && index < CODE_LENGTH - 1) {
      inputsRef.current[index + 1]?.focus();
    }
  };

  const handleKeyDown = (index: number, e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Backspace" && !digits[index] && index > 0) {
      inputsRef.current[index - 1]?.focus();
    }
    if (e.key === "ArrowLeft" && index > 0) {
      inputsRef.current[index - 1]?.focus();
    }
    if (e.key === "ArrowRight" && index < CODE_LENGTH - 1) {
      inputsRef.current[index + 1]?.focus();
    }
  };

  const handleResend = async () => {
    try {
      await resend.mutateAsync();
      setDidResend(true);
      setCooldown(COOLDOWN_SECONDS);
    } catch {
      // already verified → useAuth effect will redirect
    }
  };

  // After successful confirm the UI briefly flashes success before router.push
  if (confirm.isSuccess) {
    return (
      <AuthLayout title="Email verified" subtitle="Welcome aboard.">
        <div className="flex items-center gap-3 rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800 dark:border-emerald-500/30 dark:bg-emerald-500/10 dark:text-emerald-200">
          <CheckCircle2 className="h-4 w-4 shrink-0" />
          Redirecting to your dashboard...
        </div>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout
      title="Check your inbox"
      subtitle={
        user?.email
          ? `Enter the 6-digit code we sent to ${user.email}.`
          : "Enter the 6-digit code we just emailed you."
      }
    >
      <div className="space-y-6">
        <div className="flex items-start gap-3 rounded-lg border border-border bg-muted/40 p-4 text-sm">
          <Mail className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
          <p className="text-xs text-muted-foreground">
            The code expires in 15 minutes. Check spam if you don&apos;t see it.
          </p>
        </div>

        {/* OTP-style input grid */}
        <div className="flex justify-center gap-2">
          {digits.map((digit, i) => (
            <input
              key={i}
              ref={(el) => {
                inputsRef.current[i] = el;
              }}
              type="text"
              inputMode="numeric"
              autoComplete="one-time-code"
              maxLength={CODE_LENGTH}
              value={digit}
              onChange={(e) => handleChange(i, e.target.value)}
              onKeyDown={(e) => handleKeyDown(i, e)}
              disabled={confirm.isPending}
              className={cn(
                "h-12 w-10 rounded-lg border border-border bg-background text-center text-lg font-semibold tracking-wider",
                "outline-none transition-colors",
                "focus:border-primary focus:ring-2 focus:ring-primary/30",
                "disabled:cursor-not-allowed disabled:opacity-60",
                confirm.isError &&
                  "border-destructive/60 ring-1 ring-destructive/30",
              )}
            />
          ))}
        </div>

        {confirm.isPending && (
          <div className="flex items-center justify-center gap-2 text-xs text-muted-foreground">
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
            Verifying...
          </div>
        )}

        {confirm.isError && (
          <div className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-center text-sm text-destructive">
            Invalid or expired code. Try again or resend.
          </div>
        )}

        <Button
          type="button"
          variant="outline"
          className="w-full gap-2"
          onClick={handleResend}
          disabled={resend.isPending || cooldown > 0}
        >
          {resend.isPending ? (
            <>
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              Sending...
            </>
          ) : cooldown > 0 ? (
            `Resend in ${cooldown}s`
          ) : didResend ? (
            "Resend code"
          ) : (
            "I didn't get a code"
          )}
        </Button>

        <div className="space-y-2 pt-1 text-center">
          <p className="text-xs text-muted-foreground">
            Wrong account?{" "}
            <button
              type="button"
              onClick={() => logout.mutate()}
              className="text-primary hover:underline font-medium"
            >
              Sign out
            </button>
          </p>
          <Link
            href="/login"
            className="inline-block text-xs text-muted-foreground/70 transition-colors hover:text-foreground"
          >
            Use a different email
          </Link>
        </div>
      </div>
    </AuthLayout>
  );
}
