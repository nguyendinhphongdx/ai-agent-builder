"use client";

import { useState } from "react";
import { Loader2, Plug } from "lucide-react";
import { Button } from "@/components/ui/button";
import { oauthConnectorsService } from "@/lib/api/oauthConnectorsService";

interface ConnectButtonProps {
  provider: string;
  label: string;
  /** Where the BE should redirect the browser after the provider
   *  approves. Defaults to the current page so the user lands back
   *  where they clicked. */
  returnTo?: string;
  /** When ``false``, the button is disabled with a hint that the
   *  deployment hasn't wired the provider's client id / secret. */
  configured?: boolean;
  variant?: "default" | "outline" | "ghost";
  size?: "default" | "sm";
}

/**
 * Single-purpose CTA — clicks call ``/oauth-connectors/{p}/start``,
 * receive an authorize URL, and replace ``window.location`` with it
 * so the provider's consent screen renders top-level (cookies +
 * CSRF state survive). The post-consent callback is handled by the
 * backend; the user lands back at ``returnTo`` with
 * ``?oauth=success&connection_id=...&provider=...``.
 */
export function ConnectButton({
  provider,
  label,
  returnTo,
  configured = true,
  variant = "outline",
  size = "sm",
}: ConnectButtonProps) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onClick = async () => {
    setError(null);
    setBusy(true);
    try {
      const { authorize_url } = await oauthConnectorsService.start(
        provider,
        returnTo ?? (typeof window !== "undefined" ? window.location.pathname + window.location.search : undefined),
      );
      // Replace so the user can't "back-button" into the broken
      // pre-consent state and re-fire a stale state token.
      window.location.replace(authorize_url);
    } catch (e) {
      const message =
        (e as { response?: { data?: { detail?: string } }; message?: string })
          ?.response?.data?.detail ||
        (e as { message?: string })?.message ||
        "Failed to start OAuth";
      setError(message);
      setBusy(false);
    }
  };

  return (
    <div className="inline-flex flex-col items-end gap-1">
      <Button
        type="button"
        variant={variant}
        size={size}
        onClick={onClick}
        disabled={busy || !configured}
        title={configured ? undefined : "Not configured on this deployment"}
      >
        {busy ? (
          <Loader2 className="mr-1 h-3 w-3 animate-spin" />
        ) : (
          <Plug className="mr-1 h-3 w-3" />
        )}
        Connect {label}
      </Button>
      {error && (
        <span className="text-[10px] text-rose-600">{error}</span>
      )}
    </div>
  );
}
