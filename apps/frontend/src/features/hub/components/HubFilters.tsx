"use client";

import { Search, X } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { TEMPLATE_CATEGORIES, type BrowseFilters } from "../types";

interface HubFiltersProps {
  filters: BrowseFilters;
  onChange: (next: BrowseFilters) => void;
  /** Total item count to show beside the active-filter summary. */
  resultCount?: number;
}

const SORT_OPTIONS = [
  { value: "popular", label: "Popular" },
  { value: "newest", label: "Newest" },
  { value: "top-rated", label: "Top rated" },
  { value: "cheapest", label: "Cheapest" },
] as const;

const PRICING_OPTIONS = [
  { value: "", label: "All" },
  { value: "free", label: "Free" },
  { value: "paid", label: "Paid" },
] as const;

/**
 * Horizontal filter toolbar for the Hub browse grid.
 *
 * Layout:
 *   Row 1 — wide search + sort dropdown + pricing toggle group
 *   Row 2 — horizontal category chip strip (scrolls on narrow widths)
 *   Row 3 — active-filter summary + Clear all (only when filters set)
 *
 * Keeps the page width for the template grid (replaces the previous
 * 260px sidebar) — meaningful on this page since cards benefit from
 * a 4-up layout once the user has more than a handful of templates.
 */
export function HubFilters({ filters, onChange, resultCount }: HubFiltersProps) {
  const set = <K extends keyof BrowseFilters>(key: K, value: BrowseFilters[K]) => {
    const next = { ...filters, [key]: value };
    if (!value) delete next[key];
    onChange(next);
  };

  const activeCount = countActive(filters);

  return (
    <div className="space-y-3">
      {/* ─── Row 1: search + sort + pricing ─────────────────────────── */}
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative min-w-[200px] flex-1">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={filters.q ?? ""}
            onChange={(e) => set("q", e.target.value || undefined)}
            placeholder="Search templates by name, author, or tag…"
            className="h-9 pl-8 text-sm"
          />
        </div>

        <PricingToggle
          value={filters.pricing ?? ""}
          onChange={(v) =>
            set("pricing", (v || undefined) as BrowseFilters["pricing"])
          }
        />

        <SortMenu
          value={filters.sort ?? "popular"}
          onChange={(v) => set("sort", v)}
        />
      </div>

      {/* ─── Row 2: category chip strip ──────────────────────────────── */}
      <div className="-mx-1 flex gap-1.5 overflow-x-auto px-1 pb-1">
        <CategoryChip
          active={!filters.category}
          onClick={() => set("category", undefined)}
        >
          All
        </CategoryChip>
        {TEMPLATE_CATEGORIES.map((cat) => (
          <CategoryChip
            key={cat.value}
            active={filters.category === cat.value}
            onClick={() => set("category", cat.value)}
          >
            {cat.label}
          </CategoryChip>
        ))}
      </div>

      {/* ─── Row 3: active-filter summary ────────────────────────────── */}
      {(activeCount > 0 || typeof resultCount === "number") && (
        <div className="flex items-center justify-between gap-2 text-xs text-muted-foreground">
          <div className="flex items-center gap-2">
            {typeof resultCount === "number" && (
              <span>
                {resultCount} template{resultCount !== 1 ? "s" : ""}
              </span>
            )}
            {activeCount > 0 && (
              <>
                <span aria-hidden>·</span>
                <span>{activeCount} filter{activeCount !== 1 ? "s" : ""} applied</span>
              </>
            )}
          </div>
          {activeCount > 0 && (
            <Button
              type="button"
              variant="ghost"
              size="xs"
              onClick={() => onChange({ sort: filters.sort ?? "popular" })}
              className="text-muted-foreground hover:text-foreground"
            >
              <X />
              Clear all
            </Button>
          )}
        </div>
      )}
    </div>
  );
}

/* ─── Sub-components ─────────────────────────────────────────────── */

function PricingToggle({
  value,
  onChange,
}: {
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div
      role="group"
      aria-label="Pricing"
      className="inline-flex shrink-0 rounded-md border border-border bg-card p-0.5"
    >
      {PRICING_OPTIONS.map((opt) => {
        const active = value === opt.value;
        return (
          <button
            key={opt.value}
            type="button"
            onClick={() => onChange(opt.value)}
            className={cn(
              "rounded px-2.5 py-1 text-xs font-medium transition-colors",
              active
                ? "bg-primary text-primary-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}

function SortMenu({
  value,
  onChange,
}: {
  value: BrowseFilters["sort"];
  onChange: (v: BrowseFilters["sort"]) => void;
}) {
  return (
    <select
      value={value ?? "popular"}
      onChange={(e) => onChange(e.target.value as BrowseFilters["sort"])}
      aria-label="Sort"
      className="h-9 shrink-0 rounded-md border border-border bg-card px-2.5 text-xs font-medium outline-none transition-colors hover:bg-accent focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
    >
      {SORT_OPTIONS.map((opt) => (
        <option key={opt.value} value={opt.value}>
          Sort: {opt.label}
        </option>
      ))}
    </select>
  );
}

function CategoryChip({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "whitespace-nowrap rounded-full border px-3 py-1 text-xs font-medium transition-colors",
        active
          ? "border-primary bg-primary text-primary-foreground"
          : "border-border bg-background text-muted-foreground hover:border-border/80 hover:bg-accent hover:text-foreground",
      )}
    >
      {children}
    </button>
  );
}

/* ─── Helpers ────────────────────────────────────────────────────── */

function countActive(f: BrowseFilters): number {
  let n = 0;
  if (f.q) n++;
  if (f.category) n++;
  if (f.tag) n++;
  if (f.pricing) n++;
  return n;
}
