"use client";

import { useEffect, useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import Link from "next/link";
import { Eye, EyeOff, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { useLogin, useVerifyMfaLogin } from "../hooks/useAuth";
import { isMfaChallenge } from "../services/authService";
import { SocialAuthButtons } from "./SocialAuthButtons";

const LAST_EMAIL_KEY = "auth:lastEmail";
const REMEMBER_ME_KEY = "auth:rememberMe";

const schema = z.object({
  email: z.string().email("Invalid email"),
  password: z.string().min(6, "Password must be at least 6 characters"),
});

type FormValues = z.infer<typeof schema>;

export function LoginForm() {
  const login = useLogin();
  const verifyMfa = useVerifyMfaLogin();
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);
  const [shake, setShake] = useState(false);
  // Holds the MFA challenge state between password-step and code-step.
  // Cleared back to null on successful verify (handled by useVerifyMfaLogin
  // routing away).
  const [mfaChallenge, setMfaChallenge] = useState<string | null>(null);
  const [mfaCode, setMfaCode] = useState("");
  const formRef = useRef<HTMLFormElement>(null);

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { email: "", password: "" },
  });

  // Prefill last email if user asked to remember
  useEffect(() => {
    if (typeof window === "undefined") return;
    const remembered = localStorage.getItem(REMEMBER_ME_KEY) === "1";
    if (remembered) {
      const email = localStorage.getItem(LAST_EMAIL_KEY) ?? "";
      if (email) form.setValue("email", email);
      setRememberMe(true);
    }
  }, [form]);

  // Shake on error
  useEffect(() => {
    if (!login.error) return;
    setShake(true);
    const t = setTimeout(() => setShake(false), 500);
    return () => clearTimeout(t);
  }, [login.error]);

  // Cmd/Ctrl + Enter submits from anywhere inside the form
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
        e.preventDefault();
        formRef.current?.requestSubmit();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  const onSubmit = (data: FormValues) => {
    if (typeof window !== "undefined") {
      if (rememberMe) {
        localStorage.setItem(LAST_EMAIL_KEY, data.email);
        localStorage.setItem(REMEMBER_ME_KEY, "1");
      } else {
        localStorage.removeItem(LAST_EMAIL_KEY);
        localStorage.removeItem(REMEMBER_ME_KEY);
      }
    }
    login.mutate(
      { ...data, remember_me: rememberMe },
      {
        onSuccess: (res) => {
          if (isMfaChallenge(res)) {
            setMfaChallenge(res.mfa_token);
            setMfaCode("");
          }
        },
      },
    );
  };

  const submitMfa = () => {
    if (!mfaChallenge || !mfaCode.trim()) return;
    verifyMfa.mutate({
      mfa_token: mfaChallenge,
      code: mfaCode.trim(),
      remember_me: rememberMe,
    });
  };

  const handleDemo = () => {
    toast.info("Demo mode is coming soon");
  };

  if (mfaChallenge) {
    return (
      <div className="space-y-5">
        <div>
          <h2 className="text-lg font-semibold">Two-factor authentication</h2>
          <p className="mt-1 text-xs text-muted-foreground">
            Enter the 6-digit code from your authenticator app, or a backup
            code if you've lost access.
          </p>
        </div>
        <Input
          autoFocus
          value={mfaCode}
          onChange={(e) => setMfaCode(e.target.value)}
          placeholder="000000 or backup code"
          className="font-mono tracking-widest text-center text-lg"
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              submitMfa();
            }
          }}
        />
        {verifyMfa.error && (
          <div className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
            Invalid code — try again.
          </div>
        )}
        <Button
          className="w-full gap-2"
          onClick={submitMfa}
          disabled={verifyMfa.isPending || !mfaCode.trim()}
        >
          {verifyMfa.isPending ? (
            <>
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              Verifying...
            </>
          ) : (
            "Sign in"
          )}
        </Button>
        <button
          type="button"
          onClick={() => {
            setMfaChallenge(null);
            setMfaCode("");
          }}
          className="w-full text-center text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
          ← Back to password
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {/* Social auth */}
      <SocialAuthButtons />

      {/* Divider */}
      <div className="relative">
        <div className="absolute inset-0 flex items-center">
          <span className="w-full border-t border-border" />
        </div>
        <div className="relative flex justify-center text-[10px] uppercase tracking-wider">
          <span className="bg-background px-2 text-muted-foreground">Or continue with email</span>
        </div>
      </div>

      <Form {...form}>
        <form
          ref={formRef}
          onSubmit={form.handleSubmit(onSubmit)}
          className={cn("space-y-4", shake && "animate-shake")}
        >
          <FormField
            control={form.control}
            name="email"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Email</FormLabel>
                <FormControl>
                  <Input placeholder="you@example.com" autoComplete="email" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="password"
            render={({ field }) => (
              <FormItem>
                <div className="flex items-center justify-between">
                  <FormLabel>Password</FormLabel>
                  <Link
                    href="/forgot-password"
                    className="text-xs text-muted-foreground hover:text-foreground transition-colors"
                  >
                    Forgot password?
                  </Link>
                </div>
                <FormControl>
                  <div className="relative">
                    <Input
                      type={showPassword ? "text" : "password"}
                      placeholder="Enter your password"
                      autoComplete="current-password"
                      className="pr-10"
                      {...field}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                      tabIndex={-1}
                    >
                      {showPassword ? (
                        <EyeOff className="h-4 w-4" />
                      ) : (
                        <Eye className="h-4 w-4" />
                      )}
                    </button>
                  </div>
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          {/* Remember me */}
          <label className="flex items-center gap-2 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={rememberMe}
              onChange={(e) => setRememberMe(e.target.checked)}
              className="h-3.5 w-3.5 rounded border-border text-primary focus:ring-primary/30 cursor-pointer"
            />
            <span className="text-xs text-muted-foreground">Remember me on this device</span>
          </label>

          {login.error && (
            <div className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
              Invalid email or password
            </div>
          )}

          <Button type="submit" className="w-full gap-2" disabled={login.isPending}>
            {login.isPending ? (
              <>
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                Signing in...
              </>
            ) : (
              "Sign in"
            )}
          </Button>

          {/* Shortcut hint */}
          <p className="text-center text-[10px] text-muted-foreground/70">
            Press <kbd className="rounded border border-border bg-muted px-1 py-px font-mono text-[9px]">⌘</kbd>
            {" + "}
            <kbd className="rounded border border-border bg-muted px-1 py-px font-mono text-[9px]">Enter</kbd>
            {" "}to sign in
          </p>

          <div className="space-y-2 pt-2">
            <button
              type="button"
              onClick={handleDemo}
              className="w-full text-center text-xs text-muted-foreground hover:text-foreground transition-colors"
            >
              Try without signing up →
            </button>

            <p className="text-center text-sm text-muted-foreground">
              Don&apos;t have an account?{" "}
              <Link href="/register" className="text-primary hover:underline font-medium">
                Sign up
              </Link>
            </p>
          </div>
        </form>
      </Form>
    </div>
  );
}
