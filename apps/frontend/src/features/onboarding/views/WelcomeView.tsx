"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { Loader2, Sparkles, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useBrowseTemplates, useForkTemplate } from "@/features/hub/hooks/useTemplates";
import type { TemplateSummary } from "@/features/hub/types";

/** First-run wizard. Lists the official "starter"-tagged templates so a
 *  brand-new user can fork one in a single click instead of staring at
 *  an empty Libraries page. Falls back to a "browse the Hub" CTA if the
 *  starter templates haven't been seeded yet. */
export function WelcomeView() {
  const router = useRouter();
  const { data, isLoading } = useBrowseTemplates({ tag: "starter", sort: "newest", limit: 12 });
  const fork = useForkTemplate();

  const starters = data?.items ?? [];

  return (
    <div className="mx-auto flex min-h-screen max-w-5xl flex-col px-4 py-12">
      <header className="mb-10 text-center">
        <div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
          <Sparkles className="h-6 w-6 text-primary" />
        </div>
        <h1 className="font-heading text-3xl font-semibold tracking-tight">
          Welcome to AgentForge
        </h1>
        <p className="mx-auto mt-3 max-w-2xl text-sm text-muted-foreground">
          Start with one of these official templates — fork it, swap the model,
          tweak the prompt, and you have a working agent in seconds. You can
          always start blank from the Libraries page later.
        </p>
      </header>

      {isLoading ? (
        <div className="flex flex-1 items-center justify-center">
          <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
        </div>
      ) : starters.length === 0 ? (
        <EmptyStarters />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {starters.map((t) => (
            <StarterCard
              key={t.id}
              template={t}
              loading={fork.isPending && fork.variables === t.id}
              onPick={() => fork.mutate(t.id)}
            />
          ))}
        </div>
      )}

      <footer className="mt-10 flex items-center justify-center gap-3 text-xs text-muted-foreground">
        <button
          type="button"
          className="underline-offset-2 hover:text-foreground hover:underline"
          onClick={() => router.replace("/ws/libraries")}
        >
          Skip — start from scratch
        </button>
        <span>·</span>
        <Link href="/hub" className="underline-offset-2 hover:text-foreground hover:underline">
          Browse the full Hub
        </Link>
      </footer>
    </div>
  );
}

function StarterCard({
  template,
  onPick,
  loading,
}: {
  template: TemplateSummary;
  onPick: () => void;
  loading: boolean;
}) {
  return (
    <article className="group flex h-full flex-col rounded-xl border border-border bg-card p-5 transition-colors hover:border-primary/40">
      <div className="mb-3 flex items-center gap-2">
        <span className="rounded-full bg-violet-500/10 px-2 py-0.5 text-[10px] font-medium text-violet-700 dark:text-violet-300">
          {template.category ?? "Starter"}
        </span>
        {template.is_featured && (
          <span className="rounded-full bg-amber-500/10 px-2 py-0.5 text-[10px] font-medium text-amber-700 dark:text-amber-300">
            Official
          </span>
        )}
      </div>

      <h3 className="mb-1.5 text-sm font-semibold leading-tight">{template.title}</h3>
      <p className="mb-4 flex-1 text-xs text-muted-foreground line-clamp-3">
        {template.description}
      </p>

      <Button onClick={onPick} disabled={loading} size="sm" className="w-full">
        {loading ? (
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
        ) : (
          <>
            Use this template
            <ArrowRight className="ml-1 h-3.5 w-3.5" />
          </>
        )}
      </Button>
    </article>
  );
}

function EmptyStarters() {
  return (
    <div className="rounded-xl border border-dashed border-border p-8 text-center">
      <p className="text-sm text-muted-foreground">
        No starter templates installed yet. Browse the Hub to find something to fork,
        or start from scratch in your Libraries.
      </p>
      <div className="mt-4 flex justify-center gap-3">
        <Button asChild size="sm" variant="outline">
          <Link href="/hub">Browse Hub</Link>
        </Button>
        <Button asChild size="sm">
          <Link href={"/ws/libraries"}>Go to Libraries</Link>
        </Button>
      </div>
    </div>
  );
}
