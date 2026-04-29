"use client";

import { useEffect, useState } from "react";
import { Loader2, Save, ShieldCheck } from "lucide-react";
import { toast } from "sonner";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAuth, useUpdateMe } from "@/features/auth/hooks/useAuth";
import {
  SettingsCard,
  SettingsField,
  SettingsPageHeader,
  SettingsStack,
} from "../components/SettingsPrimitives";

/**
 * Self-edit profile (name + avatar URL). Email + role + verification flags
 * stay read-only here — email change goes through a verification flow,
 * role/verified are admin-controlled.
 */
export function ProfileView() {
  const { user } = useAuth();
  const update = useUpdateMe();

  const [fullName, setFullName] = useState("");
  const [avatarUrl, setAvatarUrl] = useState("");

  useEffect(() => {
    setFullName(user?.full_name ?? "");
    setAvatarUrl(user?.avatar_url ?? "");
  }, [user?.full_name, user?.avatar_url]);

  if (!user) {
    return (
      <div className="flex h-32 items-center justify-center">
        <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const dirty =
    fullName !== (user.full_name ?? "") || avatarUrl !== (user.avatar_url ?? "");

  const handleSave = () => {
    update.mutate(
      { full_name: fullName || null, avatar_url: avatarUrl || null },
      {
        onSuccess: () => toast.success("Profile updated"),
        onError: (err) =>
          toast.error(err instanceof Error ? err.message : "Update failed"),
      },
    );
  };

  const handleReset = () => {
    setFullName(user.full_name ?? "");
    setAvatarUrl(user.avatar_url ?? "");
  };

  const initials = (fullName || user.email)
    .split(/[\s@.]+/)
    .filter(Boolean)
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  return (
    <div>
      <SettingsPageHeader
        title="Profile"
        description="How your name and avatar appear to other users — including on Hub templates you publish."
      />

      <SettingsStack>
        <SettingsCard
          title="Public identity"
          description="Live preview reflects what other users see."
        >
          <div className="flex flex-col gap-6 sm:flex-row sm:items-start">
            {/* Live avatar + identity preview */}
            <div className="flex items-center gap-4 sm:w-48 sm:flex-col sm:items-start sm:text-left">
              <Avatar className="h-16 w-16 border border-border">
                {avatarUrl && <AvatarImage src={avatarUrl} />}
                <AvatarFallback className="text-base">{initials}</AvatarFallback>
              </Avatar>
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold">
                  {fullName || "Unnamed"}
                </p>
                <p className="truncate text-[11px] text-muted-foreground">
                  {user.email}
                </p>
              </div>
            </div>

            {/* Editable fields */}
            <div className="flex-1 space-y-4">
              <SettingsField
                label="Full name"
                hint="Default Hub author name when publishing."
                htmlFor="profile-full-name"
              >
                <Input
                  id="profile-full-name"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="Your name"
                  maxLength={255}
                />
              </SettingsField>

              <SettingsField
                label="Avatar URL"
                hint="Public image URL. Leave empty to fall back to initials."
                htmlFor="profile-avatar"
              >
                <Input
                  id="profile-avatar"
                  type="url"
                  value={avatarUrl}
                  onChange={(e) => setAvatarUrl(e.target.value)}
                  placeholder="https://…"
                  maxLength={512}
                />
              </SettingsField>
            </div>
          </div>
        </SettingsCard>

        <SettingsCard
          title="Account"
          description="Locked fields. Email change goes through a separate verification flow; role is admin-controlled."
        >
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <SettingsField label="Email">
              <Input value={user.email} disabled />
            </SettingsField>
            <SettingsField label="Status">
              <div className="flex h-9 items-center gap-2 rounded-md border border-border bg-muted/30 px-3">
                {user.is_verified ? (
                  <>
                    <ShieldCheck className="h-3.5 w-3.5 text-emerald-500" />
                    <span className="text-xs">Verified</span>
                  </>
                ) : (
                  <span className="text-xs text-muted-foreground">Unverified</span>
                )}
                {user.role !== "user" && (
                  <span className="ml-auto rounded-full bg-violet-500/10 px-2 py-0.5 text-[10px] font-medium capitalize text-violet-700 dark:text-violet-300">
                    {user.role}
                  </span>
                )}
              </div>
            </SettingsField>
          </div>
        </SettingsCard>
      </SettingsStack>

      {/* Sticky save bar — only visible when there are unsaved changes. */}
      {dirty && (
        <div className="sticky bottom-4 z-10 mt-6 flex items-center gap-3 rounded-xl border border-border bg-background/95 px-4 py-3 shadow-md backdrop-blur">
          <span className="text-xs font-medium">Unsaved changes</span>
          <div className="ml-auto flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleReset}
              disabled={update.isPending}
            >
              Reset
            </Button>
            <Button
              size="sm"
              onClick={handleSave}
              disabled={update.isPending}
              className="gap-1.5"
            >
              {update.isPending ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Save className="h-3.5 w-3.5" />
              )}
              Save
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
