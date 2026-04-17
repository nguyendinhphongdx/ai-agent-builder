"use client";

import { useRef, useState } from "react";
import { Camera, Info, X, Loader2 } from "lucide-react";
import { Input } from "@/components/ui/input";
import {
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import type { UseFormReturn } from "react-hook-form";
import type { AgentEditorFormValues } from "./types";
import { uploadService } from "@/lib/api/uploadService";
import { agentService } from "../../services/agentService";

interface BasicInfoCardProps {
  form: UseFormReturn<AgentEditorFormValues>;
  agentId?: string;
  currentAvatarUrl?: string | null;
  onAvatarFileReady?: (file: File | null) => void;
}

export function BasicInfoCard({ form, agentId, currentAvatarUrl, onAvatarFileReady }: BasicInfoCardProps) {
  const [avatarPreview, setAvatarPreview] = useState<string | null>(currentAvatarUrl ?? null);
  const [isUploading, setIsUploading] = useState(false);
  const avatarInputRef = useRef<HTMLInputElement>(null);

  const handleAvatarChange = async (file: File) => {
    setAvatarPreview(URL.createObjectURL(file));

    if (!agentId) {
      onAvatarFileReady?.(file);
      return;
    }

    setIsUploading(true);
    try {
      const uploaded = await uploadService.upload(file, "avatar", {
        entityType: "agent",
        entityId: agentId,
      });
      if (uploaded.url) {
        setAvatarPreview(uploaded.url);
        await agentService.update(agentId, { avatar_url: uploaded.url });
      }
    } catch {
      // Keep local preview on error
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="rounded-xl border border-border bg-linear-to-b from-muted/40 to-background p-4">
      <div className="mb-4 flex items-start gap-2">
        <div className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-md border border-primary/30 bg-primary/10">
          <Info className="h-3.5 w-3.5 text-primary" />
        </div>
        <div>
          <p className="text-sm font-medium">Basic Info</p>
          <p className="text-xs text-muted-foreground mt-0.5">
            Name, description, and avatar.
          </p>
        </div>
      </div>

      <div className="flex gap-4">
        {/* Avatar upload */}
        <div className="flex flex-col items-center gap-1.5">
          <div
            role="button"
            tabIndex={0}
            className="relative flex h-22 w-22 cursor-pointer items-center justify-center overflow-hidden rounded-2xl border-2 border-dashed border-border bg-muted/60 transition-colors hover:border-primary/50 hover:bg-muted"
            onClick={() => avatarInputRef.current?.click()}
            onKeyDown={(e) => e.key === "Enter" && avatarInputRef.current?.click()}
          >
            {avatarPreview ? (
              <img src={avatarPreview} alt="Avatar" className="h-full w-full object-cover" />
            ) : (
              <Camera className="h-6 w-6 text-muted-foreground/50" />
            )}
            {isUploading && (
              <div className="absolute inset-0 flex items-center justify-center bg-background/60">
                <Loader2 className="h-5 w-5 animate-spin text-primary" />
              </div>
            )}
            {avatarPreview && !isUploading && (
              <button
                type="button"
                className="absolute right-1 top-1 flex h-5 w-5 items-center justify-center rounded-full border border-border bg-background/90 shadow-sm hover:bg-background"
                onClick={(e) => {
                  e.stopPropagation();
                  setAvatarPreview(null);
                  if (avatarInputRef.current) avatarInputRef.current.value = "";
                }}
              >
                <X className="h-3 w-3" />
              </button>
            )}
          </div>
          <input
            ref={avatarInputRef}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) handleAvatarChange(file);
            }}
          />
          <span className="text-[11px] text-muted-foreground">Avatar</span>
        </div>

        {/* Name + Description */}
        <div className="flex flex-1 flex-col gap-3">
          <FormField
            control={form.control}
            name="name"
            render={({ field }) => (
              <FormItem>
                <FormLabel>
                  Name <span className="text-destructive">*</span>
                </FormLabel>
                <FormControl>
                  <Input placeholder="e.g. Research Assistant" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="description"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Description</FormLabel>
                <FormControl>
                  <Input placeholder="Short description of the agent..." {...field} />
                </FormControl>
              </FormItem>
            )}
          />
        </div>
      </div>
    </div>
  );
}
