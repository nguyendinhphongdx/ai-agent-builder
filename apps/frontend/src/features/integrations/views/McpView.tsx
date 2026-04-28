"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  Bot,
  CheckCircle2,
  ExternalLink,
  Loader2,
  RefreshCw,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { TokenPicker } from "../components/TokenPicker";
import { ConfigSnippet } from "../components/ConfigSnippet";
import {
  integrationStatusService,
  type McpStatusResponse,
} from "@/lib/api/integrationStatusService";

const REQUIRED_SCOPES = ["agents:read", "agents:chat"];

const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

const CLAUDE_DESKTOP_TEMPLATE = `{
  "mcpServers": {
    "lc-agent": {
      "command": "npx",
      "args": ["-y", "lc-agent-mcp@latest"],
      "env": {
        "AGENTFORGE_API_URL": "{{api_url}}",
        "AGENTFORGE_API_TOKEN": "{{token}}"
      }
    }
  }
}`;

const TEST_INSTALL_CMD = `npx -y lc-agent-mcp@latest`;

export function McpView() {
  const [tokenId, setTokenId] = useState<string | null>(null);
  const [status, setStatus] = useState<McpStatusResponse | null>(null);
  const [loadingStatus, setLoadingStatus] = useState(false);

  useEffect(() => {
    if (!tokenId) {
      setStatus(null);
      return;
    }
    setLoadingStatus(true);
    integrationStatusService
      .mcp(tokenId)
      .then(setStatus)
      .catch(() => setStatus(null))
      .finally(() => setLoadingStatus(false));
  }, [tokenId]);

  const refresh = async () => {
    if (!tokenId) return;
    setLoadingStatus(true);
    try {
      setStatus(await integrationStatusService.mcp(tokenId));
    } finally {
      setLoadingStatus(false);
    }
  };

  // We can't show plaintext (only stored as hash). Snippet uses prefix as a
  // placeholder hint — user pastes their saved value before running.
  const tokenHint = status
    ? // status comes from /integrations/mcp/status which doesn't return prefix;
      // we just put a sentinel here. Token picker shows the prefix separately.
      "afpt_…YOUR_TOKEN…"
    : "afpt_…YOUR_TOKEN…";

  const ready = !!status && status.token_ok && status.agents.length > 0;

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="border-b border-border px-6 py-3.5">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Link
            href="/settings/integrations"
            className="inline-flex items-center gap-1 hover:text-foreground"
          >
            <ArrowLeft className="h-3 w-3" />
            Integrations
          </Link>
          <span>/</span>
          <span className="text-foreground">MCP Server</span>
        </div>
        <div className="mt-1 flex items-start justify-between gap-4">
          <div>
            <h1 className="flex items-center gap-2 text-lg font-semibold">
              <Bot className="h-5 w-5 text-orange-500" />
              MCP Server
            </h1>
            <p className="mt-0.5 text-xs text-muted-foreground">
              Cho phép Claude Desktop, Cursor… gọi các agent của bạn như tools.
            </p>
          </div>
          {ready && (
            <Badge className="gap-1 bg-emerald-500/15 text-emerald-700 dark:text-emerald-400">
              <CheckCircle2 className="h-3 w-3" />
              Ready
            </Badge>
          )}
        </div>
      </div>

      <div className="scrollbar-thin flex-1 overflow-auto p-6">
        <div className="mx-auto max-w-3xl space-y-6">
          {/* Step 1: Pick token */}
          <Step
            n={1}
            title="Choose API token"
            description="Token cần scope agents:read + agents:chat để MCP server gọi được API."
          >
            <TokenPicker
              requiredScopes={REQUIRED_SCOPES}
              value={tokenId}
              onChange={setTokenId}
            />
          </Step>

          {/* Step 2: Install — npx is zero-install */}
          <Step
            n={2}
            title="Test connection (optional)"
            description="Có thể chạy thử bằng tay để verify package + token trước khi paste config vào Claude Desktop."
          >
            <ConfigSnippet
              template={`AGENTFORGE_API_URL="{{api_url}}" \\
AGENTFORGE_API_TOKEN="{{token}}" \\
${TEST_INSTALL_CMD}`}
              vars={{ api_url: API_URL, token: tokenHint }}
              language="bash"
              title="Run locally"
            />
            <p className="mt-2 text-[11px] text-muted-foreground">
              Server in stderr: <code className="rounded bg-muted px-1 font-mono">registered N tool(s)</code> nếu thành công. Ctrl+C để dừng — chỉ là test.
            </p>
          </Step>

          {/* Step 3: Add to Claude Desktop config */}
          <Step
            n={3}
            title="Add to Claude Desktop"
            description="Mở config file rồi merge snippet bên dưới. Dán plaintext token đã copy lúc tạo."
          >
            <div className="mb-2 space-y-1 rounded-md border border-border bg-muted/30 p-3 text-[11px]">
              <p className="font-semibold">Config file location:</p>
              <ul className="space-y-0.5 font-mono text-[10px] text-muted-foreground">
                <li>
                  <span className="font-sans text-foreground">macOS:</span>{" "}
                  ~/Library/Application Support/Claude/claude_desktop_config.json
                </li>
                <li>
                  <span className="font-sans text-foreground">Windows:</span>{" "}
                  %APPDATA%\Claude\claude_desktop_config.json
                </li>
              </ul>
            </div>
            <ConfigSnippet
              template={CLAUDE_DESKTOP_TEMPLATE}
              vars={{ api_url: API_URL, token: tokenHint }}
              language="json"
              title="claude_desktop_config.json"
            />
            <p className="mt-2 text-[11px] text-muted-foreground">
              Nếu bạn đã có <code className="rounded bg-muted px-1 font-mono">mcpServers</code> khác,
              chỉ thêm phần <code className="rounded bg-muted px-1 font-mono">"lc-agent": {"{ ... }"}</code>{" "}
              vào trong nó.
            </p>
          </Step>

          {/* Step 4: Restart Claude + verify */}
          <Step
            n={4}
            title="Restart Claude Desktop & verify"
            description="Thoát hoàn toàn rồi mở lại. MCP server sẽ tự kết nối khi Claude khởi động."
          >
            <div className="rounded-lg border border-border bg-card/80 p-4">
              <div className="mb-3 flex items-center justify-between">
                <p className="text-xs font-semibold">Connection status</p>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={refresh}
                  disabled={!tokenId || loadingStatus}
                  className="h-7 gap-1.5 text-[11px]"
                >
                  <RefreshCw
                    className={cn(
                      "h-3 w-3",
                      loadingStatus && "animate-spin",
                    )}
                  />
                  Refresh
                </Button>
              </div>

              {!tokenId ? (
                <p className="text-[11px] text-muted-foreground">
                  Chọn token ở Step 1 để check.
                </p>
              ) : loadingStatus && !status ? (
                <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
                  <Loader2 className="h-3 w-3 animate-spin" />
                  Checking…
                </div>
              ) : !status ? (
                <p className="text-[11px] text-destructive">
                  Failed to fetch status.
                </p>
              ) : (
                <div className="space-y-2 text-[11px]">
                  <Row
                    label="Token last used"
                    value={
                      status.token_last_used_at ? (
                        new Date(status.token_last_used_at).toLocaleString()
                      ) : (
                        <span className="text-muted-foreground">
                          Chưa từng dùng — restart Claude rồi nhắn 1 message để
                          trigger.
                        </span>
                      )
                    }
                  />
                  <Row
                    label="Token scopes"
                    value={
                      status.missing_scopes.length === 0 ? (
                        <span className="text-emerald-600 dark:text-emerald-400">
                          ✓ Đủ
                        </span>
                      ) : (
                        <span className="text-amber-600 dark:text-amber-400">
                          Thiếu: {status.missing_scopes.join(", ")}
                        </span>
                      )
                    }
                  />
                  <Row
                    label="Agents available"
                    value={`${status.agents.length} agent${status.agents.length === 1 ? "" : "s"}`}
                  />
                </div>
              )}
            </div>
          </Step>

          {/* Tools preview */}
          {status && status.agents.length > 0 && (
            <Step
              n={5}
              title="Tools that will appear in Claude"
              description="Mỗi agent thành 1 MCP tool riêng. Claude sẽ pick dựa trên description."
            >
              <div className="space-y-2">
                {status.agents.map((a) => (
                  <div
                    key={a.id}
                    className="flex items-start gap-3 rounded-lg border border-border bg-card/60 p-3"
                  >
                    <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md border border-orange-500/30 bg-orange-500/10">
                      <Bot className="h-3.5 w-3.5 text-orange-500" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-[11px] font-semibold">
                          {a.tool_name}
                        </code>
                        <span className="text-[10px] text-muted-foreground">
                          → {a.name}
                        </span>
                      </div>
                      {a.description && (
                        <p className="mt-1 line-clamp-2 text-[11px] text-muted-foreground">
                          {a.description}
                        </p>
                      )}
                      <p className="mt-1 font-mono text-[10px] text-muted-foreground/70">
                        model: {a.model_id}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </Step>
          )}

          {/* Help link */}
          <div className="rounded-lg border border-border bg-muted/30 p-4 text-xs">
            <p className="mb-1 font-semibold">More info</p>
            <ul className="space-y-1 text-muted-foreground">
              <li>
                Package source:{" "}
                <a
                  href="https://www.npmjs.com/package/lc-agent-mcp"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-primary hover:underline"
                >
                  npmjs.com/package/lc-agent-mcp
                  <ExternalLink className="h-2.5 w-2.5" />
                </a>
              </li>
              <li>
                MCP protocol:{" "}
                <a
                  href="https://modelcontextprotocol.io"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-primary hover:underline"
                >
                  modelcontextprotocol.io
                  <ExternalLink className="h-2.5 w-2.5" />
                </a>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ─── Step shell ────────────────────────────────────────────────── */

function Step({
  n,
  title,
  description,
  children,
}: {
  n: number;
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-xl border border-border bg-card/80 p-5">
      <div className="mb-3 flex items-start gap-3">
        <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-primary/30 bg-primary/10 text-xs font-semibold text-primary">
          {n}
        </span>
        <div>
          <h2 className="text-sm font-semibold">{title}</h2>
          <p className="mt-0.5 text-xs text-muted-foreground">{description}</p>
        </div>
      </div>
      <div className="pl-10">{children}</div>
    </section>
  );
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-3">
      <span className="shrink-0 text-muted-foreground">{label}</span>
      <span className="text-right">{value}</span>
    </div>
  );
}
