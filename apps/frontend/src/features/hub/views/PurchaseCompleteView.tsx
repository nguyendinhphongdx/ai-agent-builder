"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { CheckCircle2, Loader2, AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { usePurchaseStatus } from "../hooks/useTemplates";

/**
 * Landing page after Stripe Checkout — Stripe redirects here with a
 * ``session_id`` query param. We poll the backend until the webhook
 * has flipped the Purchase to ``paid`` and forked the agent, then
 * jump to the new agent.
 */
export function PurchaseCompleteView() {
  const router = useRouter();
  const params = useSearchParams();
  const sessionId = params.get("session_id");

  const { data, isError } = usePurchaseStatus(sessionId);

  // Auto-navigate the moment the agent is forked.
  useEffect(() => {
    if (data?.agent_id) {
      router.replace(`/agents/${data.agent_id}`);
    }
  }, [data?.agent_id, router]);

  if (!sessionId) {
    return <Card icon="error" title="Missing session id" body="Open this page from a Stripe redirect." />;
  }
  if (isError) {
    return (
      <Card
        icon="error"
        title="Couldn't read purchase status"
        body="If your card was charged, your agent will appear in your library shortly."
      >
        <Button asChild variant="outline" size="sm">
          <Link href="/agents">Go to my agents</Link>
        </Button>
      </Card>
    );
  }
  if (!data) {
    return <Card icon="loading" title="Confirming payment…" body="Waiting for Stripe to settle the charge." />;
  }
  if (data.status === "paid" && !data.agent_id) {
    return <Card icon="loading" title="Setting up your agent…" body="Cloning the template into your library." />;
  }
  if (data.status === "paid" && data.agent_id) {
    // useEffect above will redirect — show a brief spinner in the meantime.
    return <Card icon="success" title="Done!" body="Taking you to your new agent…" />;
  }
  if (data.status === "pending") {
    return <Card icon="loading" title="Processing payment…" body="This usually takes a few seconds." />;
  }
  return (
    <Card
      icon="error"
      title="Payment did not complete"
      body="No charge was made. You can try again from the template page."
    >
      <Button asChild size="sm">
        <Link href={`/hub/${data.template_id}`}>Back to template</Link>
      </Button>
    </Card>
  );
}

function Card({
  icon,
  title,
  body,
  children,
}: {
  icon: "loading" | "success" | "error";
  title: string;
  body: string;
  children?: React.ReactNode;
}) {
  const Icon = icon === "success" ? CheckCircle2 : icon === "error" ? AlertTriangle : Loader2;
  const colour =
    icon === "success"
      ? "text-emerald-500"
      : icon === "error"
        ? "text-red-500"
        : "text-muted-foreground";

  return (
    <div className="mx-auto flex min-h-[60vh] max-w-md items-center justify-center px-4">
      <div className="w-full space-y-3 rounded-xl border border-border bg-card p-8 text-center">
        <Icon
          className={`mx-auto h-10 w-10 ${colour} ${icon === "loading" ? "animate-spin" : ""}`}
        />
        <h1 className="text-base font-semibold">{title}</h1>
        <p className="text-xs text-muted-foreground">{body}</p>
        {children && <div className="pt-2">{children}</div>}
      </div>
    </div>
  );
}
