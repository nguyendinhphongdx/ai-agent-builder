"use client";

import { useState } from "react";
import { CreditCard, Loader2, RotateCcw } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useAdminPurchases, useRefundPurchase } from "../hooks/useAdmin";
import type { AdminPurchaseRow } from "../types";

const STATUS_FILTERS = [
  { value: "", label: "All" },
  { value: "paid", label: "Paid" },
  { value: "pending", label: "Pending" },
  { value: "refunded", label: "Refunded" },
  { value: "failed", label: "Failed" },
];

export function PurchasesTab() {
  const [status, setStatus] = useState("paid");
  const { data: purchases, isLoading } = useAdminPurchases({
    status: status || undefined,
  });

  return (
    <div className="space-y-4">
      <div className="flex gap-1">
        {STATUS_FILTERS.map((s) => (
          <button
            key={s.value}
            onClick={() => setStatus(s.value)}
            className={`rounded-full border px-2.5 py-1 text-[11px] transition-colors ${
              status === s.value
                ? "border-violet-500 bg-violet-500 text-white"
                : "border-border text-muted-foreground hover:bg-accent"
            }`}
          >
            {s.label}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="flex h-32 items-center justify-center">
          <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
        </div>
      ) : !purchases || purchases.length === 0 ? (
        <p className="rounded-xl border border-dashed border-border bg-card py-12 text-center text-xs text-muted-foreground">
          No purchases.
        </p>
      ) : (
        <div className="space-y-2">
          {purchases.map((p) => (
            <PurchaseRow key={p.id} purchase={p} />
          ))}
        </div>
      )}
    </div>
  );
}

function PurchaseRow({ purchase }: { purchase: AdminPurchaseRow }) {
  const refund = useRefundPurchase();

  const handleRefund = () => {
    const reason = window.prompt(
      `Refund ${formatCents(purchase.price_paid_cents)} to ${purchase.buyer_email ?? "buyer"}?\n\nOptional reason:`,
    );
    if (reason === null) return; // cancelled
    refund.mutate({ id: purchase.id, reason: reason || undefined });
  };

  return (
    <div className="flex items-center gap-3 rounded-xl border border-border bg-card p-3">
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-emerald-100 dark:bg-emerald-500/15">
        <CreditCard className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
      </div>

      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-1.5">
          <span className="text-sm font-semibold">
            {formatCents(purchase.price_paid_cents)}
          </span>
          <StatusBadge status={purchase.status} />
        </div>
        <p className="text-[11px] text-muted-foreground">
          {purchase.template_title ?? "Template"} →{" "}
          {purchase.buyer_email ?? "(unknown buyer)"}
          {" · "}
          {new Date(purchase.purchased_at).toLocaleString()}
        </p>
      </div>

      {purchase.status === "paid" && purchase.price_paid_cents > 0 && (
        <Button
          variant="outline"
          size="sm"
          className="gap-1.5"
          onClick={handleRefund}
          disabled={refund.isPending}
        >
          <RotateCcw className="h-3 w-3" />
          Refund
        </Button>
      )}
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const colours: Record<string, string> = {
    paid: "border-emerald-500/40 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300",
    pending: "border-amber-500/40 bg-amber-500/10 text-amber-700 dark:text-amber-300",
    refunded: "border-border bg-muted text-muted-foreground",
    failed: "border-red-500/40 bg-red-500/10 text-red-700 dark:text-red-300",
  };
  return (
    <Badge variant="outline" className={`text-[10px] ${colours[status] ?? ""}`}>
      {status}
    </Badge>
  );
}

function formatCents(cents: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(cents / 100);
}
