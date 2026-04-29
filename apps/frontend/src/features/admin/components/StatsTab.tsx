"use client";

import { Loader2, Users, Sparkles, GitBranch, DollarSign, TrendingUp } from "lucide-react";
import { useAdminStats } from "../hooks/useAdmin";

export function StatsTab() {
  const { data, isLoading } = useAdminStats();

  if (isLoading) {
    return (
      <div className="flex h-32 items-center justify-center">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    );
  }
  if (!data) return null;

  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
      <Card icon={Users} label="Users (total)" value={data.total_users.toLocaleString()} />
      <Card icon={Users} label="Active 30d" value={data.active_users_30d.toLocaleString()} />
      <Card
        icon={Sparkles}
        label="Templates"
        value={`${data.published_templates} / ${data.total_templates}`}
        sub="published / total"
      />
      <Card icon={GitBranch} label="Forks (lifetime)" value={data.total_forks.toLocaleString()} />
      <Card
        icon={DollarSign}
        label="Revenue (30d)"
        value={formatCents(data.revenue_cents_30d)}
      />
      <Card
        icon={DollarSign}
        label="Revenue (all time)"
        value={formatCents(data.revenue_cents_all_time)}
      />
      <Card
        icon={TrendingUp}
        label="Purchases (paid)"
        value={data.total_purchases_paid.toLocaleString()}
      />
    </div>
  );
}

function Card({
  icon: Icon,
  label,
  value,
  sub,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string;
  sub?: string;
}) {
  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <div className="flex items-center gap-2 text-[11px] font-medium text-muted-foreground">
        <Icon className="h-3 w-3" />
        {label}
      </div>
      <p className="mt-2 text-xl font-semibold">{value}</p>
      {sub && <p className="text-[10px] text-muted-foreground">{sub}</p>}
    </div>
  );
}

function formatCents(cents: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(cents / 100);
}
