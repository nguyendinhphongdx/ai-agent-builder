"use client";

import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  Bot,
  CheckCircle2,
  Database,
  GitCommit,
  Loader2,
  Sparkles,
  Users,
  Wrench,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  useTemplate,
  useForkTemplate,
  usePurchaseTemplate,
  useTemplateVersions,
} from "../hooks/useTemplates";
import { ReviewsSection } from "../components/ReviewsSection";
import { formatPrice } from "../lib/price";
import { useAuth } from "@/features/auth/hooks/useAuth";

interface HubDetailViewProps {
  slugOrId: string;
}

export function HubDetailView({ slugOrId }: HubDetailViewProps) {
  const router = useRouter();
  const { data: template, isLoading } = useTemplate(slugOrId);
  const { data: versions } = useTemplateVersions(template?.id ?? "");
  const { isAuthenticated } = useAuth();
  const fork = useForkTemplate();
  const purchase = usePurchaseTemplate();

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!template) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-12 text-center">
        <p className="text-sm text-muted-foreground">Template not found.</p>
      </div>
    );
  }

  const isFree = template.price_cents === 0;
  const priceLabel = isFree ? "Get for free" : formatPrice(template.price_cents, template.currency);

  return (
    <div className="mx-auto max-w-5xl px-4 py-6">
      <button
        onClick={() => router.back()}
        className="mb-4 flex items-center gap-1.5 text-xs text-muted-foreground transition-colors hover:text-foreground"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        Back
      </button>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_320px]">
        {/* Left: details */}
        <div className="space-y-6">
          {/* Header */}
          <div>
            <div className="mb-2 flex items-center gap-2">
              {template.is_featured && (
                <Badge className="gap-1 bg-amber-500 text-white border-0">
                  <Sparkles className="h-3 w-3" />
                  Featured
                </Badge>
              )}
              {template.category && (
                <Badge variant="secondary" className="text-[10px]">
                  {template.category}
                </Badge>
              )}
            </div>
            <h1 className="font-heading text-2xl font-semibold">{template.title}</h1>
            <p className="mt-1 text-xs text-muted-foreground">
              by {template.author_name}
              {template.published_at && (
                <> · published {new Date(template.published_at).toLocaleDateString()}</>
              )}
            </p>
          </div>

          {/* Cover */}
          <div className="relative aspect-[16/9] overflow-hidden rounded-xl bg-gradient-to-br from-violet-100 to-violet-200 dark:from-violet-500/20 dark:to-violet-700/20">
            {template.cover_image_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={template.cover_image_url}
                alt={template.title}
                className="h-full w-full object-cover"
              />
            ) : (
              <div className="flex h-full items-center justify-center">
                <Bot className="h-16 w-16 text-violet-500/60" />
              </div>
            )}
          </div>

          {/* Description */}
          {template.description && (
            <section className="space-y-2">
              <h2 className="text-sm font-semibold">About this agent</h2>
              <p className="whitespace-pre-wrap text-sm text-muted-foreground">
                {template.description}
              </p>
            </section>
          )}

          {/* What's included */}
          {template.snapshot && <SnapshotPreview snapshot={template.snapshot} />}

          {/* Tags */}
          {template.tags.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {template.tags.map((tag) => (
                <Badge key={tag} variant="outline" className="text-[10px]">
                  #{tag}
                </Badge>
              ))}
            </div>
          )}

          {/* Version history */}
          {versions && versions.length > 0 && (
            <section className="space-y-3">
              <h2 className="text-sm font-semibold">Version history</h2>
              <ul className="space-y-2">
                {versions.map((v) => (
                  <li
                    key={v.id}
                    className="rounded-lg border border-border bg-card p-3"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <GitCommit className="h-3 w-3 text-muted-foreground" />
                        <span className="font-mono text-xs font-medium">v{v.version}</span>
                        {v.is_current && (
                          <Badge variant="secondary" className="text-[10px]">
                            Current
                          </Badge>
                        )}
                      </div>
                      <span className="text-[10px] text-muted-foreground">
                        {new Date(v.created_at).toLocaleDateString()}
                      </span>
                    </div>
                    {v.changelog && (
                      <p className="mt-1.5 whitespace-pre-wrap text-[11px] text-muted-foreground">
                        {v.changelog}
                      </p>
                    )}
                  </li>
                ))}
              </ul>
            </section>
          )}

          {/* Reviews */}
          <ReviewsSection templateId={template.id} canReview={isAuthenticated} />
        </div>

        {/* Right: action sidebar */}
        <aside>
          <div className="sticky top-4 space-y-4 rounded-xl border border-border bg-card p-5">
            <div className="space-y-1">
              <p
                className={`text-2xl font-bold ${
                  isFree ? "text-emerald-600 dark:text-emerald-400" : "text-foreground"
                }`}
              >
                {priceLabel}
              </p>
              {!isFree && (
                <p className="text-[11px] text-muted-foreground">
                  Secure checkout via Stripe
                </p>
              )}
            </div>

            {isFree ? (
              <Button
                onClick={() => fork.mutate(template.id)}
                disabled={fork.isPending}
                className="w-full gap-1.5"
                size="lg"
              >
                {fork.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <CheckCircle2 className="h-4 w-4" />
                )}
                {fork.isPending ? "Forking…" : "Get this agent"}
              </Button>
            ) : (
              <Button
                onClick={() => purchase.mutate(template.id)}
                disabled={purchase.isPending}
                className="w-full gap-1.5"
                size="lg"
              >
                {purchase.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <CheckCircle2 className="h-4 w-4" />
                )}
                {purchase.isPending ? "Redirecting…" : `Buy for ${priceLabel}`}
              </Button>
            )}
            {purchase.isError && (
              <p className="rounded-md border border-red-500/30 bg-red-500/5 px-2.5 py-1.5 text-[11px] text-red-700 dark:text-red-300">
                {(purchase.error as Error)?.message ?? "Checkout failed"}
              </p>
            )}

            <p className="text-[10px] text-muted-foreground">
              {isFree
                ? "Forking creates a new agent in your library. You can edit it freely."
                : "Pay once, install whenever. Tools are cloned; knowledge bases are empty shells."}
            </p>

            <div className="space-y-2 border-t border-border pt-4 text-xs">
              <Stat icon={Users} label="Forks" value={template.fork_count.toLocaleString()} />
              {template.snapshot && (
                <>
                  <Stat
                    icon={Wrench}
                    label="Tools"
                    value={String(template.snapshot.metadata.tool_count ?? 0)}
                  />
                  <Stat
                    icon={Database}
                    label="Knowledge bases"
                    value={String(template.snapshot.metadata.kb_count ?? 0)}
                  />
                </>
              )}
              {template.current_version && (
                <Stat icon={Bot} label="Version" value={template.current_version} />
              )}
            </div>

            {template.snapshot?.metadata.required_credentials &&
              template.snapshot.metadata.required_credentials.length > 0 && (
                <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-3">
                  <p className="text-[11px] font-medium text-amber-700 dark:text-amber-300">
                    Requires credential
                  </p>
                  <p className="mt-1 text-[11px] text-muted-foreground">
                    Connect {template.snapshot.metadata.required_credentials.join(", ")} after
                    forking.
                  </p>
                </div>
              )}
          </div>
        </aside>
      </div>
    </div>
  );
}

function SnapshotPreview({
  snapshot,
}: {
  snapshot: NonNullable<ReturnType<typeof useTemplate>["data"]>["snapshot"];
}) {
  if (!snapshot) return null;
  return (
    <section className="space-y-3">
      <h2 className="text-sm font-semibold">What's included</h2>

      <div className="rounded-lg border border-border bg-card p-4">
        <p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
          System prompt
        </p>
        <pre className="mt-2 max-h-40 overflow-auto whitespace-pre-wrap text-xs text-muted-foreground">
          {snapshot.agent.system_prompt}
        </pre>
      </div>

      {snapshot.tools.length > 0 && (
        <div className="rounded-lg border border-border bg-card p-4">
          <p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
            Tools ({snapshot.tools.length})
          </p>
          <ul className="mt-2 space-y-1.5">
            {snapshot.tools.map((t, i) => (
              <li key={i} className="flex items-start gap-2 text-xs">
                <Wrench className="mt-0.5 h-3 w-3 shrink-0 text-muted-foreground" />
                <div>
                  <p className="font-medium">{t.name}</p>
                  <p className="text-[11px] text-muted-foreground">{t.description}</p>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}

      {snapshot.knowledge_bases.length > 0 && (
        <div className="rounded-lg border border-border bg-card p-4">
          <p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
            Knowledge bases ({snapshot.knowledge_bases.length})
          </p>
          <p className="mt-1 text-[11px] text-muted-foreground">
            Configuration is included; you'll upload your own documents after forking.
          </p>
          <ul className="mt-2 space-y-1">
            {snapshot.knowledge_bases.map((kb, i) => (
              <li key={i} className="text-xs">
                <span className="font-medium">{kb.name}</span>
                {kb.description && <span className="text-muted-foreground"> — {kb.description}</span>}
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}

function Stat({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-center justify-between">
      <span className="flex items-center gap-1.5 text-muted-foreground">
        <Icon className="h-3 w-3" />
        {label}
      </span>
      <span className="font-medium">{value}</span>
    </div>
  );
}
