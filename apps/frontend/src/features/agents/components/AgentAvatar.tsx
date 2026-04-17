"use client";

import { Bot } from "lucide-react";
import { cn } from "@/lib/utils";

interface AgentAvatarProps {
  avatarUrl?: string | null;
  name?: string;
  size?: "sm" | "md" | "lg";
  className?: string;
}

const sizes = {
  sm: "h-8 w-8 rounded-lg",
  md: "h-9 w-9 rounded-lg",
  lg: "h-12 w-12 rounded-xl",
};

const iconSizes = {
  sm: "h-3.5 w-3.5",
  md: "h-4 w-4",
  lg: "h-5 w-5",
};

export function AgentAvatar({ avatarUrl, name, size = "md", className }: AgentAvatarProps) {
  if (avatarUrl) {
    return (
      <img
        src={avatarUrl}
        alt={name || "Agent"}
        className={cn(sizes[size], "object-cover", className)}
      />
    );
  }

  return (
    <div className={cn(sizes[size], "flex items-center justify-center border border-primary/20 bg-primary/10", className)}>
      <Bot className={cn(iconSizes[size], "text-primary")} />
    </div>
  );
}
