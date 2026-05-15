"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Loader2, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAcceptInvitation } from "../hooks/useWorkspaces";

/**
 * Anonymous-friendly landing page for invitation links. If the user
 * isn't signed in we punt them to /login with a return-to that
 * funnels back here — the apiClient's 401 interceptor handles the
 * redirect path automatically.
 */
export function AcceptInvitationView({ token }: { token: string }) {
  const router = useRouter();
  const qc = useQueryClient();
  const accept = useAcceptInvitation();
  const [status, setStatus] = useState<"idle" | "accepting" | "ok" | "fail">("idle");
  const [error, setError] = useState<string | null>(null);
  const [workspaceName, setWorkspaceName] = useState<string | null>(null);

  useEffect(() => {
    if (status !== "idle") return;
    setStatus("accepting");
    accept
      .mutateAsync(token)
      .then((res) => {
        setWorkspaceName(res.workspace.name);
        setStatus("ok");
        qc.invalidateQueries();
      })
      .catch((e) => {
        const msg =
          e?.response?.data?.detail ||
          (e instanceof Error ? e.message : "Failed to accept invitation");
        setError(msg);
        setStatus("fail");
      });
    // accept hook is stable via useMutation; safe to omit from deps to
    // avoid re-running on every render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  return (
    <div className="flex min-h-[60vh] items-center justify-center p-6">
      <div className="w-full max-w-md rounded-xl border border-border bg-card p-8 text-center shadow-sm">
        {status === "accepting" && (
          <>
            <Loader2 className="mx-auto mb-3 h-8 w-8 animate-spin text-muted-foreground" />
            <p className="text-sm text-muted-foreground">Accepting invitation…</p>
          </>
        )}
        {status === "ok" && (
          <>
            <CheckCircle2 className="mx-auto mb-3 h-10 w-10 text-emerald-500" />
            <h1 className="text-lg font-semibold">Welcome to {workspaceName}</h1>
            <p className="mt-1 text-xs text-muted-foreground">
              Bạn đã join workspace thành công.
            </p>
            <Button
              className="mt-5"
              onClick={() => router.push("/org")}
            >
              Go to dashboard
            </Button>
          </>
        )}
        {status === "fail" && (
          <>
            <XCircle className="mx-auto mb-3 h-10 w-10 text-destructive" />
            <h1 className="text-lg font-semibold">Can't accept this invitation</h1>
            <p className="mt-1 text-xs text-destructive">{error}</p>
            <p className="mt-2 text-[11px] text-muted-foreground">
              Có thể link đã hết hạn hoặc đã được dùng. Liên hệ người mời để
              gửi lại invitation mới.
            </p>
            <Button
              variant="outline"
              className="mt-5"
              onClick={() => router.push("/org")}
            >
              Back to org
            </Button>
          </>
        )}
      </div>
    </div>
  );
}
