"use client";

import Link from "next/link";
import {
  ArrowRight,
  BookOpen,
  Bot,
  Code,
  Globe,
  MessageSquare,
  Share2,
  type LucideIcon,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { SettingsPageHeader } from "@/features/settings/components/SettingsPrimitives";

type IntegrationStatus = "available" | "coming-soon";

interface Integration {
  slug: string;
  title: string;
  description: string;
  icon: LucideIcon;
  iconColor: string;
  status: IntegrationStatus;
  href?: string;
}

const INTEGRATIONS: Integration[] = [
  {
    slug: "api-docs",
    title: "REST API",
    description: "cURL, Python, JavaScript — tích hợp trực tiếp qua HTTP.",
    icon: Code,
    iconColor: "text-violet-500",
    status: "available",
    href: "/settings/integrations/api-docs",
  },
  {
    slug: "mcp",
    title: "MCP Server",
    description: "Agents trở thành tools cho Claude Desktop, Cursor.",
    icon: Bot,
    iconColor: "text-orange-500",
    status: "available",
    href: "/settings/integrations/mcp",
  },
  {
    slug: "embed",
    title: "Web Embed",
    description: "Nhúng chat widget vào website chỉ với 1 thẻ <script>.",
    icon: Globe,
    iconColor: "text-sky-500",
    status: "available",
    href: "/settings/integrations/embed",
  },
  {
    slug: "slack",
    title: "Slack Bot",
    description: "Mention agent trong Slack channel hoặc DM.",
    icon: MessageSquare,
    iconColor: "text-emerald-500",
    status: "coming-soon",
  },
  {
    slug: "share",
    title: "Share Link",
    description: "URL anonymous để khách demo agent không cần đăng ký.",
    icon: Share2,
    iconColor: "text-pink-500",
    status: "coming-soon",
  },
];

export function IntegrationsHubView() {
  return (
    <div>
      <SettingsPageHeader
        title="Integrations"
        description="Đưa agents ra ngoài hệ thống — qua REST API, MCP, embed widget hoặc bot."
      />

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        {INTEGRATIONS.map((it) => (
          <IntegrationCard key={it.slug} integration={it} />
        ))}
      </div>

      <div className="mt-6 rounded-xl border border-border bg-muted/20 p-4">
        <div className="flex items-start gap-3">
          <BookOpen className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
          <div className="space-y-1 text-xs text-muted-foreground">
            <p className="font-medium text-foreground">Before you start</p>
            <p>
              Every integration needs an API token. Create one at{" "}
              <Link href="/settings/api-tokens" className="text-primary hover:underline">
                Settings → API Tokens
              </Link>{" "}
              then return here to wire each channel.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ─── Card ──────────────────────────────────────────────────────── */

function IntegrationCard({ integration }: { integration: Integration }) {
  const Icon = integration.icon;
  const isAvailable = integration.status === "available";

  const inner = (
    <div
      className={cn(
        "group flex h-full flex-col gap-3 rounded-xl border bg-card/80 p-5 shadow-sm transition-all",
        isAvailable
          ? "border-border hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-md"
          : "border-border/60 opacity-70",
      )}
    >
      <div className="flex items-start justify-between">
        <div
          className={cn(
            "flex h-10 w-10 items-center justify-center rounded-lg border border-border bg-muted",
          )}
        >
          <Icon className={cn("h-5 w-5", integration.iconColor)} />
        </div>
        {!isAvailable && (
          <span className="rounded-full border border-border bg-background px-2 py-0.5 text-[10px] uppercase tracking-wider text-muted-foreground">
            Coming soon
          </span>
        )}
      </div>

      <div className="flex-1">
        <h3 className="text-sm font-semibold">{integration.title}</h3>
        <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
          {integration.description}
        </p>
      </div>

      {isAvailable && (
        <div className="flex items-center gap-1 text-xs font-medium text-primary">
          Setup
          <ArrowRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" />
        </div>
      )}
    </div>
  );

  if (isAvailable && integration.href) {
    return <Link href={integration.href}>{inner}</Link>;
  }
  return inner;
}
