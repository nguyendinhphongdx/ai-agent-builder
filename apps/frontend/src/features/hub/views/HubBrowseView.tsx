"use client";

import { useState } from "react";
import Link from "next/link";
import { Loader2, Bot } from "lucide-react";
import { TemplateCard } from "../components/TemplateCard";
import { HubFilters } from "../components/HubFilters";
import { useBrowseTemplates } from "../hooks/useTemplates";
import type { BrowseFilters } from "../types";

export function HubBrowseView() {
  const [filters, setFilters] = useState<BrowseFilters>({ sort: "popular" });
  const { data, isLoading } = useBrowseTemplates(filters);

  return (
    <div className="mx-auto max-w-7xl px-4 py-6">
      <header className="mb-6 flex items-end justify-between gap-4">
        <div className="space-y-1">
          <h1 className="font-heading text-2xl font-semibold">Hub</h1>
          <p className="text-sm text-muted-foreground">
            Browse agents published by the community. Fork one to get your own copy.
          </p>
        </div>
        <Link
          href="/hub/me"
          className="shrink-0 text-xs text-muted-foreground transition-colors hover:text-foreground"
        >
          My templates →
        </Link>
      </header>

      <div className="mb-5">
        <HubFilters
          filters={filters}
          onChange={setFilters}
          resultCount={data?.total}
        />
      </div>

      {isLoading ? (
        <div className="flex h-60 items-center justify-center">
          <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
        </div>
      ) : !data || data.items.length === 0 ? (
        <EmptyState query={filters.q} />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {data.items.map((t) => (
            <TemplateCard key={t.id} template={t} />
          ))}
        </div>
      )}
    </div>
  );
}

function EmptyState({ query }: { query?: string }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border bg-card py-16 text-center">
      <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-muted">
        <Bot className="h-5 w-5 text-muted-foreground/60" />
      </div>
      <p className="text-sm font-medium text-foreground">No templates found</p>
      <p className="mt-1 text-xs text-muted-foreground">
        {query
          ? `Nothing matches "${query}". Try clearing filters.`
          : "The hub is empty. Be the first to publish an agent!"}
      </p>
    </div>
  );
}
