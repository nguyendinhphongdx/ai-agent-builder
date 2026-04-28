"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  CheckCircle2,
  ExternalLink,
  Globe,
  Loader2,
  RefreshCw,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { AgentPicker } from "../components/AgentPicker";
import { ConfigSnippet } from "../components/ConfigSnippet";
import {
  agentShareService,
  type ShareConfig,
} from "@/lib/api/agentShareService";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";
const EMBED_CDN =
  process.env.NEXT_PUBLIC_EMBED_URL || `${API_URL}/static/embed.js`;

const SCRIPT_TEMPLATE = `<script
  src="{{cdn}}"
  data-token="{{token}}"
  data-api="{{api_url}}"
  data-color="{{color}}"
  defer
></script>`;

const PROGRAMMATIC_TEMPLATE = `<script src="{{cdn}}" defer></script>
<script>
  AgentForge.mount({
    token: "{{token}}",
    apiUrl: "{{api_url}}",
    color: "{{color}}",
    // target: document.getElementById("chat-slot"), // optional inline mount
  });
</script>`;

const PRESET_COLORS = [
  "#2563eb", // blue
  "#9333ea", // purple
  "#16a34a", // green
  "#ea580c", // orange
  "#e11d48", // rose
  "#0ea5e9", // sky
  "#111827", // near-black
];

const DEFAULT_COLOR = "#2563eb";

export function EmbedView() {
  const [agentId, setAgentId] = useState<string | null>(null);
  const [config, setConfig] = useState<ShareConfig | null>(null);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!agentId) {
      setConfig(null);
      return;
    }
    setLoading(true);
    agentShareService
      .get(agentId)
      .then(setConfig)
      .catch(() => setConfig(null))
      .finally(() => setLoading(false));
  }, [agentId]);

  const color =
    (typeof config?.settings?.color === "string"
      ? (config.settings.color as string)
      : null) || DEFAULT_COLOR;

  const enable = async () => {
    if (!agentId) return;
    setBusy(true);
    try {
      setConfig(await agentShareService.update(agentId, { enabled: true }));
    } finally {
      setBusy(false);
    }
  };

  const disable = async () => {
    if (!agentId || !confirm("Revoke embed? Existing widgets will stop working."))
      return;
    setBusy(true);
    try {
      setConfig(await agentShareService.update(agentId, { enabled: false }));
    } finally {
      setBusy(false);
    }
  };

  const rotate = async () => {
    if (!agentId || !confirm("Rotate token? Existing widgets must be re-deployed."))
      return;
    setBusy(true);
    try {
      setConfig(await agentShareService.update(agentId, { rotate: true }));
    } finally {
      setBusy(false);
    }
  };

  const setColor = async (c: string) => {
    if (!agentId || !config) return;
    // Optimistic update — rollback on failure.
    const prev = config;
    setConfig({ ...config, settings: { ...config.settings, color: c } });
    try {
      const next = await agentShareService.update(agentId, {
        settings: { ...config.settings, color: c },
      });
      setConfig(next);
    } catch {
      setConfig(prev);
    }
  };

  const ready = !!config?.enabled && !!config.share_token;
  const tokenHint = config?.share_token ?? "<MISSING_TOKEN>";

  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-border px-6 py-3.5">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Link
            href="/settings/integrations"
            className="inline-flex items-center gap-1 hover:text-foreground"
          >
            <ArrowLeft className="h-3 w-3" />
            Integrations
          </Link>
          <span>/</span>
          <span className="text-foreground">Web Embed</span>
        </div>
        <div className="mt-1 flex items-start justify-between gap-4">
          <div>
            <h1 className="flex items-center gap-2 text-lg font-semibold">
              <Globe className="h-5 w-5 text-sky-500" />
              Web Embed
            </h1>
            <p className="mt-0.5 text-xs text-muted-foreground">
              Một thẻ <code className="rounded bg-muted px-1 font-mono">&lt;script&gt;</code> để
              nhúng agent vào website.
            </p>
          </div>
          {ready && (
            <Badge className="gap-1 bg-emerald-500/15 text-emerald-700 dark:text-emerald-400">
              <CheckCircle2 className="h-3 w-3" />
              Live
            </Badge>
          )}
        </div>
      </div>

      <div className="scrollbar-thin flex-1 overflow-auto p-6">
        <div className="mx-auto max-w-5xl">
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1fr)_360px]">
            <div className="space-y-6">
              {/* Step 1 */}
              <Step
                n={1}
                title="Choose agent"
                description="Mỗi agent có 1 share token riêng. Đổi agent → đổi token."
              >
                <AgentPicker value={agentId} onChange={setAgentId} />
              </Step>

              {/* Step 2: Enable */}
              <Step
                n={2}
                title="Enable embed channel"
                description="Mint 1 share token public. Nhúng vào website nào cũng được."
              >
                {!agentId ? (
                  <p className="text-[11px] text-muted-foreground">
                    Chọn agent ở Step 1 trước.
                  </p>
                ) : loading ? (
                  <Loader load />
                ) : !config ? (
                  <p className="text-[11px] text-destructive">
                    Failed to load share config.
                  </p>
                ) : (
                  <div className="flex flex-wrap items-center gap-2">
                    {config.enabled ? (
                      <>
                        <Badge className="gap-1 bg-emerald-500/15 text-emerald-700 dark:text-emerald-400">
                          <CheckCircle2 className="h-3 w-3" />
                          Enabled
                        </Badge>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={rotate}
                          disabled={busy}
                          className="h-7 gap-1.5 text-[11px]"
                        >
                          <RefreshCw
                            className={cn(
                              "h-3 w-3",
                              busy && "animate-spin",
                            )}
                          />
                          Rotate token
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={disable}
                          disabled={busy}
                          className="h-7 text-[11px] text-destructive hover:bg-destructive/10 hover:text-destructive"
                        >
                          Revoke
                        </Button>
                      </>
                    ) : (
                      <Button
                        size="sm"
                        onClick={enable}
                        disabled={busy}
                        className="h-8 text-xs"
                      >
                        {busy ? (
                          <Loader2 className="h-3 w-3 animate-spin" />
                        ) : (
                          "Enable embed"
                        )}
                      </Button>
                    )}
                  </div>
                )}
              </Step>

              {/* Step 3: Customise */}
              <Step
                n={3}
                title="Customise"
                description="Theme color áp cho FAB + bubble user. Lưu ngay khi đổi."
              >
                <div className="flex flex-wrap items-center gap-2">
                  {PRESET_COLORS.map((c) => (
                    <button
                      key={c}
                      type="button"
                      onClick={() => setColor(c)}
                      disabled={!config?.enabled || busy}
                      className={cn(
                        "h-7 w-7 rounded-full border-2 transition-all",
                        color === c
                          ? "border-foreground ring-2 ring-foreground/20 ring-offset-2 ring-offset-background"
                          : "border-border hover:scale-110",
                        (!config?.enabled || busy) &&
                          "cursor-not-allowed opacity-50",
                      )}
                      style={{ backgroundColor: c }}
                      aria-label={`Color ${c}`}
                    />
                  ))}
                  <input
                    type="color"
                    value={color}
                    onChange={(e) => setColor(e.target.value)}
                    disabled={!config?.enabled || busy}
                    className="h-7 w-7 cursor-pointer rounded-full border-2 border-border bg-transparent disabled:cursor-not-allowed disabled:opacity-50"
                    aria-label="Custom color"
                  />
                  <code className="ml-2 rounded bg-muted px-2 py-1 font-mono text-[11px]">
                    {color}
                  </code>
                </div>
              </Step>

              {/* Step 4: Snippet */}
              <Step
                n={4}
                title="Paste into your website"
                description="Đặt trước </body>. Widget tự load lazy khi user click FAB."
              >
                <ConfigSnippet
                  template={SCRIPT_TEMPLATE}
                  vars={{
                    cdn: EMBED_CDN,
                    token: config?.enabled ? tokenHint : undefined,
                    api_url: API_URL,
                    color,
                  }}
                  language="html"
                  title="Drop-in script"
                />
                <details className="mt-3 group">
                  <summary className="cursor-pointer text-[11px] text-muted-foreground hover:text-foreground">
                    Programmatic mount (advanced)
                  </summary>
                  <div className="mt-2">
                    <ConfigSnippet
                      template={PROGRAMMATIC_TEMPLATE}
                      vars={{
                        cdn: EMBED_CDN,
                        token: config?.enabled ? tokenHint : undefined,
                        api_url: API_URL,
                        color,
                      }}
                      language="html"
                      title="Inline mount"
                    />
                  </div>
                </details>
              </Step>

              {/* Help */}
              <div className="rounded-lg border border-border bg-muted/30 p-4 text-xs">
                <p className="mb-1 font-semibold">Notes</p>
                <ul className="list-inside list-disc space-y-1 text-muted-foreground">
                  <li>
                    Conversation lưu cho khách (anonymous) bằng{" "}
                    <code className="rounded bg-muted px-1 font-mono">localStorage</code>{" "}
                    — refresh không mất.
                  </li>
                  <li>
                    Rate limit: 30 req/min/IP (mặc định) — chống spam khi widget public.
                  </li>
                  <li>
                    Rotate token = invalidate tất cả site đang nhúng. Phải re-deploy.
                  </li>
                  <li>
                    CSS isolated bằng Shadow DOM, không đụng style site host.
                  </li>
                </ul>
                <p className="mt-2 flex items-center gap-1 text-muted-foreground">
                  Source:{" "}
                  <a
                    href="https://github.com/your-org/lc-agent/tree/master/packages/embed-widget"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-primary hover:underline"
                  >
                    packages/embed-widget
                    <ExternalLink className="h-2.5 w-2.5" />
                  </a>
                </p>
              </div>
            </div>

            {/* Live preview */}
            <div className="lg:sticky lg:top-6 lg:self-start">
              <div className="rounded-xl border border-border bg-card/80 p-4">
                <p className="mb-3 text-xs font-semibold">Live preview</p>
                <PreviewFrame color={color} />
                <p className="mt-2 text-[10px] text-muted-foreground">
                  Visual mock — chỉ để xem theme. Test thật bằng cách paste snippet vào 1 trang HTML.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ─── Helpers ──────────────────────────────────────────────────── */

function Step({
  n,
  title,
  description,
  children,
}: {
  n: number;
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-xl border border-border bg-card/80 p-5">
      <div className="mb-3 flex items-start gap-3">
        <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-primary/30 bg-primary/10 text-xs font-semibold text-primary">
          {n}
        </span>
        <div>
          <h2 className="text-sm font-semibold">{title}</h2>
          <p className="mt-0.5 text-xs text-muted-foreground">{description}</p>
        </div>
      </div>
      <div className="pl-10">{children}</div>
    </section>
  );
}

function Loader({ load }: { load: boolean }) {
  if (!load) return null;
  return (
    <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
      <Loader2 className="h-3 w-3 animate-spin" /> Loading…
    </div>
  );
}

function PreviewFrame({ color }: { color: string }) {
  return (
    <div className="relative h-80 overflow-hidden rounded-lg border border-border bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800">
      {/* Mock site dots */}
      <div className="px-3 py-2">
        <div className="flex gap-1.5">
          <div className="h-2 w-2 rounded-full bg-red-400" />
          <div className="h-2 w-2 rounded-full bg-amber-400" />
          <div className="h-2 w-2 rounded-full bg-emerald-400" />
        </div>
      </div>
      <div className="space-y-1.5 px-4 pt-2">
        <div className="h-2 w-3/4 rounded bg-slate-300/60 dark:bg-slate-700/60" />
        <div className="h-2 w-1/2 rounded bg-slate-300/40 dark:bg-slate-700/40" />
        <div className="h-2 w-2/3 rounded bg-slate-300/50 dark:bg-slate-700/50" />
      </div>

      {/* Mock chat bubble (simulating panel) */}
      <div className="absolute bottom-14 right-3 w-44 rounded-lg bg-white p-2 shadow-lg dark:bg-slate-950">
        <div
          className="mb-1.5 flex items-center gap-1.5 rounded-t px-2 py-1 text-[9px] font-semibold text-white"
          style={{ backgroundColor: color }}
        >
          <div className="h-3 w-3 rounded-full bg-white/30" />
          Agent
        </div>
        <div className="space-y-1 px-1 pb-1">
          <div className="ml-auto w-3/4 rounded-md px-1.5 py-1 text-[8px] text-white" style={{ backgroundColor: color }}>
            Xin chào!
          </div>
          <div className="w-2/3 rounded-md border border-slate-200 bg-slate-50 px-1.5 py-1 text-[8px] dark:border-slate-700 dark:bg-slate-900">
            Tôi giúp gì được?
          </div>
        </div>
      </div>

      {/* Mock FAB */}
      <button
        type="button"
        className="absolute bottom-3 right-3 flex h-10 w-10 items-center justify-center rounded-full text-white shadow-lg"
        style={{ backgroundColor: color }}
        aria-hidden
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
          <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-2 12H6v-2h12v2zm0-3H6V9h12v2zm0-3H6V6h12v2z" />
        </svg>
      </button>
    </div>
  );
}
