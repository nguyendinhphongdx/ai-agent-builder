"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AlertCircle, ExternalLink, Loader2, Send, Sparkles } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import { usePayoutStatus } from "@/features/settings/payouts/hooks/usePayouts";
import { usePublishAgent } from "../hooks/useTemplates";
import { type Currency, providerForCurrency } from "../lib/price";
import { TEMPLATE_CATEGORIES } from "../types";

interface PublishDialogProps {
  agentId: string;
  agentName: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

type Pricing = "free" | "paid";

export function PublishDialog({
  agentId,
  agentName,
  open,
  onOpenChange,
}: PublishDialogProps) {
  const router = useRouter();
  const publish = usePublishAgent();
  const { data: payoutStatus, isLoading: payoutLoading } = usePayoutStatus();

  const [title, setTitle] = useState(agentName);
  const [description, setDescription] = useState("");
  const [authorName, setAuthorName] = useState("");
  const [category, setCategory] = useState("");
  const [tagsInput, setTagsInput] = useState("");
  const [pricing, setPricing] = useState<Pricing>("free");
  const [currency, setCurrency] = useState<Currency>("USD");
  const [priceInput, setPriceInput] = useState("9.99");

  const provider = providerForCurrency(currency);
  // Stripe authors must complete Connect onboarding before publishing paid.
  // MoMo (VND) is platform-collects in V1 — no onboarding step.
  const payoutsReady = !!payoutStatus?.charges_enabled && !!payoutStatus?.payouts_enabled;
  const needsOnboarding =
    pricing === "paid" && provider === "stripe" && !payoutLoading && !payoutsReady;

  const priceCents = (() => {
    if (pricing === "free") return 0;
    const n = Number.parseFloat(priceInput);
    if (!Number.isFinite(n) || n <= 0) return 0;
    // VND is stored as whole-unit integers (no subunits). USD/EUR/etc.
    // multiply by 100 to land in cent-based storage.
    return currency === "VND" ? Math.round(n) : Math.round(n * 100);
  })();

  const canSubmit =
    !!title.trim() &&
    !publish.isPending &&
    (pricing === "free" || (priceCents > 0 && (provider !== "stripe" || payoutsReady)));

  const handleSubmit = () => {
    if (!canSubmit) return;
    const tags = tagsInput
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean);

    publish.mutate(
      {
        agentId,
        input: {
          title: title.trim(),
          description: description.trim() || undefined,
          author_name: authorName.trim() || undefined,
          category: category || undefined,
          tags,
          price_cents: priceCents,
          currency,
        },
      },
      {
        onSuccess: (template) => {
          onOpenChange(false);
          router.push(`/hub/${template.slug}`);
        },
      },
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-violet-500" />
            Publish to Hub
          </DialogTitle>
          <DialogDescription>
            Anyone can fork this agent into their own library. Tools are cloned.
            Knowledge bases are cloned as empty shells (no documents shared).
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Title */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground">Title</label>
            <Input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Customer Support Bot"
              maxLength={200}
            />
          </div>

          {/* Description */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground">Description</label>
            <Textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What does this agent do? Include any setup notes — required credentials, expected use cases, etc."
              rows={4}
              maxLength={5000}
            />
          </div>

          {/* Author name */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground">
              Author display name (optional)
            </label>
            <Input
              value={authorName}
              onChange={(e) => setAuthorName(e.target.value)}
              placeholder="Defaults to your account name"
              maxLength={100}
            />
            <p className="text-[10px] text-muted-foreground/70">
              Free text — use a brand name if you want.
            </p>
          </div>

          {/* Category + tags */}
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground">Category</label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full rounded-md border border-border bg-background px-3 py-1.5 text-xs outline-none focus:border-primary"
              >
                <option value="">— Select —</option>
                {TEMPLATE_CATEGORIES.map((cat) => (
                  <option key={cat.value} value={cat.value}>
                    {cat.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground">
                Tags (comma-separated)
              </label>
              <Input
                value={tagsInput}
                onChange={(e) => setTagsInput(e.target.value)}
                placeholder="ecommerce, returns"
              />
            </div>
          </div>

          {/* Pricing */}
          <div className="space-y-2">
            <label className="text-xs font-medium text-muted-foreground">Pricing</label>
            <div className="flex gap-2">
              <PricingPill
                active={pricing === "free"}
                onClick={() => setPricing("free")}
                label="Free"
                hint="Anyone can fork."
              />
              <PricingPill
                active={pricing === "paid"}
                onClick={() => setPricing("paid")}
                label="Paid"
                hint="Stripe or MoMo, picked by currency."
              />
            </div>

            {pricing === "paid" && (
              <div className="space-y-2 pt-2">
                {/* Provider picker — currency defines which gateway */}
                <div className="flex gap-2">
                  <CurrencyPill
                    active={currency === "USD"}
                    onClick={() => setCurrency("USD")}
                    label="USD"
                    provider="Stripe"
                    hint="Cards · 10% platform fee · author payouts via Stripe Connect."
                  />
                  <CurrencyPill
                    active={currency === "VND"}
                    onClick={() => setCurrency("VND")}
                    label="VND"
                    provider="MoMo"
                    hint="MoMo wallet · platform settles authors manually (no Connect)."
                  />
                </div>

                <div className="flex items-center gap-2">
                  <span className="text-[11px] text-muted-foreground">Price</span>
                  <Input
                    type="number"
                    inputMode={currency === "VND" ? "numeric" : "decimal"}
                    min={currency === "VND" ? "1000" : "0.50"}
                    step={currency === "VND" ? "1000" : "0.01"}
                    value={priceInput}
                    onChange={(e) => setPriceInput(e.target.value)}
                    className="w-36"
                  />
                  <span className="text-[11px] text-muted-foreground">{currency}</span>
                  <span className="ml-auto rounded-full border border-border bg-muted/30 px-2 py-0.5 text-[10px] font-medium text-muted-foreground">
                    via {provider === "stripe" ? "Stripe" : "MoMo"}
                  </span>
                </div>
              </div>
            )}
          </div>

          {/* Connect onboarding banner — Stripe only */}
          {needsOnboarding && <PayoutOnboardingBanner connected={!!payoutStatus?.connected} />}
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={publish.isPending}
          >
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={!canSubmit} className="gap-1.5">
            {publish.isPending ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Send className="h-3.5 w-3.5" />
            )}
            Publish
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function CurrencyPill({
  active,
  onClick,
  label,
  provider,
  hint,
}: {
  active: boolean;
  onClick: () => void;
  label: string;
  provider: string;
  hint: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "flex flex-1 flex-col items-start gap-0.5 rounded-md border px-3 py-2 text-left transition-colors",
        active
          ? "border-primary bg-primary/5 text-foreground"
          : "border-border bg-background text-muted-foreground hover:border-foreground/30",
      )}
    >
      <span className="flex items-center gap-1.5 text-xs font-medium">
        {label}
        <span className="rounded-full bg-muted px-1.5 py-0.5 text-[9px] font-normal text-muted-foreground">
          {provider}
        </span>
      </span>
      <span className="text-[10px] text-muted-foreground/80">{hint}</span>
    </button>
  );
}

function PricingPill({
  active,
  onClick,
  label,
  hint,
}: {
  active: boolean;
  onClick: () => void;
  label: string;
  hint: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "flex flex-1 flex-col items-start gap-0.5 rounded-md border px-3 py-2 text-left transition-colors",
        active
          ? "border-primary bg-primary/5 text-foreground"
          : "border-border bg-background text-muted-foreground hover:border-foreground/30",
      )}
    >
      <span className="text-xs font-medium">{label}</span>
      <span className="text-[10px] text-muted-foreground/80">{hint}</span>
    </button>
  );
}

function PayoutOnboardingBanner({ connected }: { connected: boolean }) {
  return (
    <div className="flex gap-2.5 rounded-md border border-amber-500/30 bg-amber-500/5 p-3 text-[11px] text-amber-700 dark:text-amber-300">
      <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
      <div className="flex-1">
        <p className="font-medium">
          {connected
            ? "Finish Stripe onboarding before publishing paid templates."
            : "Connect a Stripe payout account before publishing paid templates."}
        </p>
        <p className="mt-0.5 text-amber-700/80 dark:text-amber-300/80">
          Stripe handles identity verification and bank linking — usually under 2 minutes.
        </p>
        <Link
          href="/settings#payouts"
          className="mt-1.5 inline-flex items-center gap-1 font-medium underline-offset-2 hover:underline"
        >
          Open Settings → Author Payouts
          <ExternalLink className="h-3 w-3" />
        </Link>
      </div>
    </div>
  );
}
