import Link from "next/link";
import {
  ArrowRight,
  Bot,
  ChevronRight,
  CornerDownLeft,
  Database,
  Sparkles,
  User,
} from "lucide-react";
import { HERO_STATS, SITE } from "../data/content";
import { GithubIcon } from "./icons";

export function Hero() {
  return (
    <section className="relative overflow-hidden">
      <BackgroundGlow />

      <div className="relative mx-auto max-w-7xl px-6 pt-24 pb-20 md:pt-32 md:pb-28 lg:px-8">
        <div className="mx-auto max-w-3xl text-center">
          <a
            href={SITE.github}
            target="_blank"
            rel="noreferrer noopener"
            className="animate-fade-up inline-flex items-center gap-2 rounded-full border border-border bg-background/60 px-4 py-1.5 text-xs font-medium text-foreground/80 backdrop-blur transition-colors hover:bg-background"
          >
            <Sparkles className="h-3.5 w-3.5 text-primary" />
            <span>Open source · MIT</span>
            <ChevronRight className="h-3 w-3 text-muted-foreground" />
          </a>

          <h1
            className="animate-fade-up mt-6 text-4xl font-extrabold leading-[1.05] tracking-tight text-foreground sm:text-5xl md:text-6xl lg:text-[4rem]"
            style={{ animationDelay: "100ms" }}
          >
            Build AI agents.{" "}
            <span className="bg-linear-to-r from-primary via-indigo-500 to-violet-500 bg-clip-text text-transparent">
              Ship them anywhere.
            </span>
          </h1>

          <p
            className="animate-fade-up mx-auto mt-6 max-w-2xl text-lg leading-relaxed text-muted-foreground md:text-xl"
            style={{ animationDelay: "200ms" }}
          >
            Connect your tools and knowledge to a chat agent. Drop it on your
            site, plug it into your app, or share it with Claude — without
            writing the plumbing.
          </p>

          <div
            className="animate-fade-up mt-10 flex flex-col items-center gap-3 sm:flex-row sm:justify-center sm:gap-4"
            style={{ animationDelay: "300ms" }}
          >
            <Link
              href="/register"
              className="inline-flex items-center justify-center gap-2 rounded-xl bg-primary px-7 py-3 text-sm font-semibold text-primary-foreground shadow-lg shadow-primary/25 transition-all hover:bg-primary/90 hover:shadow-xl hover:shadow-primary/30 active:scale-[0.98]"
            >
              Start free
              <ArrowRight className="h-4 w-4" />
            </Link>
            <a
              href={SITE.github}
              target="_blank"
              rel="noreferrer noopener"
              className="inline-flex items-center justify-center gap-2 rounded-xl border border-border bg-background px-7 py-3 text-sm font-semibold text-foreground shadow-sm transition-all hover:bg-muted"
            >
              <GithubIcon className="h-4 w-4" />
              View on GitHub
            </a>
          </div>

          <div
            className="animate-fade-up mx-auto mt-14 grid max-w-lg grid-cols-2 gap-6 sm:grid-cols-4"
            style={{ animationDelay: "400ms" }}
          >
            {HERO_STATS.map((s) => (
              <div key={s.label} className="text-center">
                <div className="text-2xl font-bold tracking-tight text-foreground">{s.value}</div>
                <div className="mt-0.5 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                  {s.label}
                </div>
              </div>
            ))}
          </div>
        </div>

        <AgentPreview />
      </div>
    </section>
  );
}

function BackgroundGlow() {
  return (
    <>
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute left-1/2 top-0 h-150 w-250 -translate-x-1/2 rounded-full bg-linear-to-b from-primary/12 via-indigo-500/8 to-transparent blur-3xl" />
        <div className="absolute right-0 top-20 h-72 w-72 rounded-full bg-amber-400/10 blur-3xl" />
        <div className="absolute left-0 top-40 h-72 w-72 rounded-full bg-emerald-400/10 blur-3xl" />
      </div>
      <div
        className="pointer-events-none absolute inset-0 opacity-[0.04] dark:opacity-[0.08]"
        style={{
          backgroundImage:
            "radial-gradient(circle, currentColor 1px, transparent 1px)",
          backgroundSize: "24px 24px",
        }}
      />
    </>
  );
}

/**
 * Hero visual: a "live" agent chat preview. Communicates the product in 2
 * seconds — anyone who has used a chat app gets it. Shows a tool-calling
 * indicator + grounded answer to demonstrate value (not just "another chat").
 */
function AgentPreview() {
  return (
    <div
      className="animate-fade-up mx-auto mt-16 max-w-3xl"
      style={{ animationDelay: "500ms" }}
    >
      <div className="overflow-hidden rounded-2xl border border-border bg-background shadow-2xl shadow-foreground/5">
        {/* Top bar — agent identity */}
        <div className="flex items-center justify-between border-b border-border bg-muted/30 px-5 py-3">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-linear-to-br from-primary to-violet-600 text-primary-foreground shadow-sm">
              <Bot className="h-4 w-4" />
            </div>
            <div className="text-left">
              <div className="text-[13px] font-semibold text-foreground">
                Customer Support Agent
              </div>
              <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                Live · GPT-4o · 3 tools · 1 knowledge base
              </div>
            </div>
          </div>
          <div className="hidden items-center gap-2 sm:flex">
            <Channel label="Chat" active />
            <Channel label="API" />
            <Channel label="MCP" />
          </div>
        </div>

        {/* Chat body */}
        <div className="space-y-4 px-5 py-6 text-left sm:px-7">
          <UserBubble>How do I reset my password?</UserBubble>

          <ToolBubble label="Searched help docs" subtle="2 results · 0.3s" />

          <BotBubble>
            To reset your password, head to{" "}
            <span className="rounded bg-muted px-1.5 py-0.5 font-mono text-[12px] font-medium text-foreground">
              Settings → Security
            </span>{" "}
            and click <strong className="font-semibold text-foreground">Reset password</strong>. You&apos;ll get an email
            within a minute.
          </BotBubble>
        </div>

        {/* Compose bar — non-interactive */}
        <div className="flex items-center gap-2 border-t border-border bg-muted/20 px-5 py-3">
          <div className="flex flex-1 items-center gap-2 rounded-lg border border-border bg-background px-3 py-2 text-[12px] text-muted-foreground/80">
            <span>Type a message…</span>
          </div>
          <button
            type="button"
            disabled
            aria-label="Send (preview)"
            className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-primary-foreground opacity-90"
          >
            <CornerDownLeft className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
}

function Channel({ label, active }: { label: string; active?: boolean }) {
  return (
    <span
      className={
        active
          ? "rounded-full bg-primary/10 px-2.5 py-1 text-[11px] font-medium text-primary"
          : "rounded-full border border-border bg-background px-2.5 py-1 text-[11px] font-medium text-muted-foreground"
      }
    >
      {label}
    </span>
  );
}

function UserBubble({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-start justify-end gap-3">
      <div className="max-w-md rounded-2xl rounded-tr-sm bg-primary px-4 py-2.5 text-sm text-primary-foreground">
        {children}
      </div>
      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-muted text-muted-foreground">
        <User className="h-3.5 w-3.5" />
      </div>
    </div>
  );
}

function BotBubble({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-start gap-3">
      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-linear-to-br from-primary to-violet-600 text-primary-foreground">
        <Bot className="h-3.5 w-3.5" />
      </div>
      <div className="max-w-md rounded-2xl rounded-tl-sm border border-border bg-background px-4 py-2.5 text-sm leading-relaxed text-foreground/90 shadow-sm">
        {children}
      </div>
    </div>
  );
}

function ToolBubble({ label, subtle }: { label: string; subtle?: string }) {
  return (
    <div className="flex items-center gap-3 pl-10">
      <span className="inline-flex items-center gap-2 rounded-full border border-emerald-500/20 bg-emerald-500/5 px-3 py-1 text-[11px] font-medium text-emerald-600 dark:text-emerald-400">
        <Database className="h-3 w-3" />
        {label}
      </span>
      {subtle && (
        <span className="text-[11px] text-muted-foreground">{subtle}</span>
      )}
    </div>
  );
}
