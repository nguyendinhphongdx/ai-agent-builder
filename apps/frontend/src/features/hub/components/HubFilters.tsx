"use client";

import { Search, SlidersHorizontal } from "lucide-react";
import { Input } from "@/components/ui/input";
import { TEMPLATE_CATEGORIES, type BrowseFilters } from "../types";

interface HubFiltersProps {
  filters: BrowseFilters;
  onChange: (next: BrowseFilters) => void;
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

export function HubFilters({ filters, onChange }: HubFiltersProps) {
  const set = <K extends keyof BrowseFilters>(key: K, value: BrowseFilters[K]) => {
    const next = { ...filters, [key]: value };
    if (!value) delete next[key];
    onChange(next);
  };

  return (
    <div className="space-y-4 rounded-xl border border-border bg-card p-4">
      <div className="flex items-center gap-2">
        <SlidersHorizontal className="h-3.5 w-3.5 text-muted-foreground" />
        <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Filter
        </span>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
        <Input
          value={filters.q ?? ""}
          onChange={(e) => set("q", e.target.value || undefined)}
          placeholder="Search templates..."
          className="pl-8 text-xs"
        />
      </div>

      {/* Category */}
      <div className="space-y-2">
        <label className="text-[11px] font-medium text-muted-foreground">Category</label>
        <div className="flex flex-wrap gap-1.5">
          <FilterPill
            active={!filters.category}
            onClick={() => set("category", undefined)}
          >
            All
          </FilterPill>
          {TEMPLATE_CATEGORIES.map((cat) => (
            <FilterPill
              key={cat.value}
              active={filters.category === cat.value}
              onClick={() => set("category", cat.value)}
            >
              {cat.label}
            </FilterPill>
          ))}
        </div>
      </div>

      {/* Pricing */}
      <div className="space-y-2">
        <label className="text-[11px] font-medium text-muted-foreground">Pricing</label>
        <div className="flex gap-1.5">
          {PRICING_OPTIONS.map((opt) => (
            <FilterPill
              key={opt.value}
              active={(filters.pricing ?? "") === opt.value}
              onClick={() => set("pricing", (opt.value || undefined) as BrowseFilters["pricing"])}
            >
              {opt.label}
            </FilterPill>
          ))}
        </div>
      </div>

      {/* Sort */}
      <div className="space-y-2">
        <label className="text-[11px] font-medium text-muted-foreground">Sort by</label>
        <select
          value={filters.sort ?? "popular"}
          onChange={(e) => set("sort", e.target.value as BrowseFilters["sort"])}
          className="w-full rounded-md border border-border bg-background px-2 py-1.5 text-xs outline-none focus:border-primary"
        >
          {SORT_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}

function FilterPill({
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
      className={`rounded-full border px-2.5 py-1 text-[11px] transition-colors ${
        active
          ? "border-violet-500 bg-violet-500 text-white"
          : "border-border text-muted-foreground hover:bg-accent"
      }`}
    >
      {children}
    </button>
  );
}
