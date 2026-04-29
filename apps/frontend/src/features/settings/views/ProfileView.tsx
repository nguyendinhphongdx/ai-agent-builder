"use client";

import { useEffect, useRef, useState } from "react";
import { ImageUp, Loader2, Save, ShieldCheck, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  useAuth,
  useUpdateMe,
  useUploadAvatar,
} from "@/features/auth/hooks/useAuth";
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
  const upload = useUploadAvatar();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [fullName, setFullName] = useState("");
  const [avatarUrl, setAvatarUrl] = useState("");

  useEffect(() => {
    setFullName(user?.full_name ?? "");
    setAvatarUrl(user?.avatar_url ?? "");
  }, [user?.full_name, user?.avatar_url]);

  const handleAvatarPick = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = ""; // reset so picking the same file again still fires
    if (!file) return;
    upload.mutate(file, {
      onSuccess: (u) => {
        setAvatarUrl(u.avatar_url ?? "");
        toast.success("Avatar updated");
      },
      onError: (err) =>
        toast.error(
          err instanceof Error ? err.message : "Couldn't upload — try a smaller PNG/JPEG",
        ),
    });
  };

  const handleAvatarRemove = () => {
    update.mutate(
      { avatar_url: null },
      {
        onSuccess: () => {
          setAvatarUrl("");
          toast.success("Avatar removed");
        },
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
            {/* Live avatar + identity preview + upload trigger */}
            <div className="flex flex-col items-start gap-3 sm:w-48">
              <div className="flex items-center gap-4 sm:flex-col sm:items-start">
                <div className="relative">
                  <Avatar className="h-20 w-20 border border-border">
                    {avatarUrl && <AvatarImage src={avatarUrl} />}
                    <AvatarFallback className="text-lg">{initials}</AvatarFallback>
                  </Avatar>
                  {upload.isPending && (
                    <div className="absolute inset-0 flex items-center justify-center rounded-full bg-background/70">
                      <Loader2 className="h-4 w-4 animate-spin" />
                    </div>
                  )}
                </div>
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold">
                    {fullName || "Unnamed"}
                  </p>
                  <p className="truncate text-[11px] text-muted-foreground">
                    {user.email}
                  </p>
                </div>
              </div>

              <input
                ref={fileInputRef}
                type="file"
                accept="image/png,image/jpeg,image/webp"
                onChange={handleAvatarPick}
                className="hidden"
              />
              <div className="flex flex-wrap gap-1.5">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={upload.isPending}
                  className="gap-1.5"
                >
                  <ImageUp className="h-3 w-3" />
                  Upload
                </Button>
                {avatarUrl && (
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={handleAvatarRemove}
                    disabled={update.isPending || upload.isPending}
                    className="gap-1.5 text-muted-foreground"
                    title="Remove avatar"
                  >
                    <Trash2 className="h-3 w-3" />
                    Remove
                  </Button>
                )}
              </div>
              <p className="text-[10px] text-muted-foreground/70">
                PNG, JPEG, or WEBP. Up to 4 MB.
              </p>
            </div>

            {/* Editable text fields */}
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
                hint="Override the uploaded image with a remote URL — useful for Gravatar / linked profiles."
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
