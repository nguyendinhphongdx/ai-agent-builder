"use client";

import { useEffect, useState } from "react";
import { Loader2, Save } from "lucide-react";
import { toast } from "sonner";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAuth, useUpdateMe } from "@/features/auth/hooks/useAuth";

/**
 * Self-edit profile (name + avatar URL). Email + role + verification flags
 * are intentionally read-only here — email change goes through a
 * verification flow, role/verified are admin-controlled.
 */
export function ProfileView() {
  const { user } = useAuth();
  const update = useUpdateMe();

  const [fullName, setFullName] = useState("");
  const [avatarUrl, setAvatarUrl] = useState("");

  // Sync local state with the cached user once it lands. Done via
  // useEffect so the form re-fills when navigating into the page after
  // the auth query was already hydrated elsewhere.
  useEffect(() => {
    setFullName(user?.full_name ?? "");
    setAvatarUrl(user?.avatar_url ?? "");
  }, [user?.full_name, user?.avatar_url]);

  const dirty =
    fullName !== (user?.full_name ?? "") ||
    avatarUrl !== (user?.avatar_url ?? "");

  const handleSave = () => {
    update.mutate(
      { full_name: fullName || null, avatar_url: avatarUrl || null },
      {
        onSuccess: () => toast.success("Profile updated"),
        onError: (err) => toast.error(err instanceof Error ? err.message : "Update failed"),
      },
    );
  };

  if (!user) {
    return (
      <div className="flex h-32 items-center justify-center">
        <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const initials = fullName
    ? fullName
        .split(" ")
        .map((n) => n[0])
        .join("")
        .slice(0, 2)
        .toUpperCase()
    : user.email[0].toUpperCase();

  return (
    <section className="space-y-6">
      <header>
        <h1 className="font-heading text-xl font-semibold">Profile</h1>
        <p className="mt-1 text-xs text-muted-foreground">
          How your name and avatar appear to other users (e.g. on Hub
          templates you publish).
        </p>
      </header>

      <div className="flex items-center gap-4 rounded-xl border border-border bg-card p-4">
        <Avatar className="h-16 w-16">
          {avatarUrl && <AvatarImage src={avatarUrl} />}
          <AvatarFallback className="text-lg">{initials}</AvatarFallback>
        </Avatar>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold">
            {fullName || "Unnamed"}
          </p>
          <p className="truncate text-xs text-muted-foreground">{user.email}</p>
          <div className="mt-1 flex flex-wrap gap-1.5">
            {user.is_verified && (
              <span className="rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-medium text-emerald-700 dark:text-emerald-300">
                Email verified
              </span>
            )}
            {user.role !== "user" && (
              <span className="rounded-full bg-violet-500/10 px-2 py-0.5 text-[10px] font-medium capitalize text-violet-700 dark:text-violet-300">
                {user.role}
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="space-y-4">
        <Field
          label="Full name"
          hint="Used for display + the default Hub author name when publishing."
        >
          <Input
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            placeholder="Your name"
            maxLength={255}
          />
        </Field>

        <Field
          label="Avatar URL"
          hint="Public image URL. Leave empty to fall back to your initials."
        >
          <Input
            value={avatarUrl}
            onChange={(e) => setAvatarUrl(e.target.value)}
            placeholder="https://..."
            maxLength={512}
            type="url"
          />
        </Field>

        <Field
          label="Email"
          hint="Email changes go through a separate verification flow — coming soon."
        >
          <Input value={user.email} disabled />
        </Field>
      </div>

      <div className="flex justify-end">
        <Button onClick={handleSave} disabled={!dirty || update.isPending} className="gap-1.5">
          {update.isPending ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <Save className="h-3.5 w-3.5" />
          )}
          Save changes
        </Button>
      </div>
    </section>
  );
}

function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <label className="text-xs font-medium text-muted-foreground">{label}</label>
      {children}
      {hint && <p className="text-[10px] text-muted-foreground/70">{hint}</p>}
    </div>
  );
}
