"use client";

import Link from "next/link";
import { ArrowRight, Boxes } from "lucide-react";

/** Pointer card on the Settings page that takes the user to the
 *  integrations hub. Kept tiny — the real catalogue lives at
 *  /settings/integrations. */
export function IntegrationsLinkSection() {
  return (
    <section>
      <Link
        href="/settings/integrations"
        className="group flex items-center gap-4 rounded-xl border border-border bg-card/80 p-4 shadow-sm transition-all hover:border-primary/40 hover:shadow-md"
      >
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-primary/20 bg-primary/10">
          <Boxes className="h-5 w-5 text-primary" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold">Integrations</p>
          <p className="mt-0.5 text-xs text-muted-foreground">
            Đưa agents ra ngoài: REST API, MCP server, embed widget, Slack bot.
          </p>
        </div>
        <ArrowRight className="h-4 w-4 shrink-0 text-muted-foreground transition-all group-hover:translate-x-0.5 group-hover:text-foreground" />
      </Link>
    </section>
  );
}
