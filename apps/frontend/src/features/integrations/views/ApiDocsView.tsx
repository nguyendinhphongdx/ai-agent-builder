"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowLeft, ExternalLink } from "lucide-react";
import { TokenPicker } from "../components/TokenPicker";
import { ConfigSnippet } from "../components/ConfigSnippet";
import { CodeBlockCopy } from "../components/CodeBlockCopy";
import {
  personalTokenService,
  type PersonalToken,
} from "@/lib/api/personalTokenService";
import { useEffect } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

const REQUIRED_SCOPES = ["agents:read", "agents:chat"];

const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

const CURL_LIST = `curl '{{api_url}}/external/agents' \\
  -H 'Authorization: Bearer {{token}}'`;

const CURL_CHAT = `curl -X POST '{{api_url}}/external/agents/{{agent_id}}/chat' \\
  -H 'Authorization: Bearer {{token}}' \\
  -H 'Content-Type: application/json' \\
  -d '{
    "message": "Xin chào, hôm nay thế nào?"
  }'`;

const CURL_STREAM = `curl -N -X POST '{{api_url}}/external/agents/{{agent_id}}/stream' \\
  -H 'Authorization: Bearer {{token}}' \\
  -H 'Content-Type: application/json' \\
  -d '{
    "message": "Stream câu trả lời cho tôi"
  }'`;

const PY_CODE = `import httpx

API_URL = "{{api_url}}"
TOKEN = "{{token}}"
AGENT_ID = "{{agent_id}}"

with httpx.Client(headers={"Authorization": f"Bearer {TOKEN}"}) as client:
    # 1. List agents
    agents = client.get(f"{API_URL}/external/agents").json()

    # 2. Send a chat turn
    res = client.post(
        f"{API_URL}/external/agents/{AGENT_ID}/chat",
        json={"message": "Xin chào!"},
        timeout=120,
    )
    print(res.json())
`;

const JS_CODE = `const API_URL = "{{api_url}}";
const TOKEN = "{{token}}";
const AGENT_ID = "{{agent_id}}";

// 1. List agents
const list = await fetch(\`\${API_URL}/external/agents\`, {
  headers: { Authorization: \`Bearer \${TOKEN}\` },
}).then((r) => r.json());

// 2. Send a chat turn
const res = await fetch(
  \`\${API_URL}/external/agents/\${AGENT_ID}/chat\`,
  {
    method: "POST",
    headers: {
      Authorization: \`Bearer \${TOKEN}\`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ message: "Xin chào!" }),
  },
).then((r) => r.json());

console.log(res);`;

export function ApiDocsView() {
  const [tokenId, setTokenId] = useState<string | null>(null);
  const [tokens, setTokens] = useState<PersonalToken[]>([]);

  useEffect(() => {
    personalTokenService.list().then(setTokens).catch(() => setTokens([]));
  }, []);

  // We don't show the plaintext (we don't have it after creation) — the user
  // pastes their saved token into the snippet. Show the prefix as a hint.
  const selected = tokens.find((t) => t.id === tokenId) ?? null;
  const tokenPlaceholder = selected ? `${selected.key_prefix}...` : "afpt_…";

  const vars = {
    api_url: API_URL,
    token: tokenPlaceholder,
    agent_id: "<agent-id>",
  };

  return (
    <div className="flex h-full flex-col">
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
          <span className="text-foreground">REST API</span>
        </div>
        <h1 className="mt-1 text-lg font-semibold">REST API</h1>
        <p className="mt-0.5 text-xs text-muted-foreground">
          Tích hợp trực tiếp qua HTTP. Mọi channel khác (MCP, embed, Slack) cũng dùng
          chính API này phía sau.
        </p>
      </div>

      <div className="scrollbar-thin flex-1 overflow-auto p-6">
        <div className="mx-auto max-w-3xl space-y-6">
          {/* Token picker */}
          <section className="rounded-xl border border-border bg-card/80 p-5">
            <p className="mb-3 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
              Step 1 · Choose token
            </p>
            <TokenPicker
              requiredScopes={REQUIRED_SCOPES}
              value={tokenId}
              onChange={setTokenId}
              label="API token"
            />
            <p className="mt-2 text-[11px] text-muted-foreground">
              ⚠ Plaintext token được show 1 lần khi tạo — paste vào snippet thay cho
              <code className="mx-1 rounded bg-muted px-1 font-mono">{tokenPlaceholder}</code>.
              Nếu mất, revoke và tạo lại trong{" "}
              <Link href="/settings" className="text-primary hover:underline">
                API Tokens
              </Link>
              .
            </p>
          </section>

          {/* Endpoint reference (compact) */}
          <section>
            <h2 className="mb-3 text-sm font-semibold">Endpoints</h2>
            <div className="overflow-hidden rounded-xl border border-border">
              <table className="w-full text-xs">
                <thead className="bg-muted/40 text-[10px] uppercase tracking-wider text-muted-foreground">
                  <tr>
                    <th className="px-3 py-2 text-left">Method</th>
                    <th className="px-3 py-2 text-left">Path</th>
                    <th className="px-3 py-2 text-left">Required scopes</th>
                  </tr>
                </thead>
                <tbody>
                  {[
                    { m: "GET", p: "/external/agents", s: ["agents:read"] },
                    { m: "POST", p: "/external/agents/{id}/chat", s: ["agents:chat"] },
                    { m: "POST", p: "/external/agents/{id}/stream", s: ["agents:chat"] },
                    {
                      m: "GET",
                      p: "/external/conversations",
                      s: ["conversations:read"],
                    },
                    {
                      m: "GET",
                      p: "/external/conversations/{id}/messages",
                      s: ["conversations:read"],
                    },
                  ].map((r) => (
                    <tr key={r.m + r.p} className="border-t border-border/60">
                      <td className="px-3 py-2 font-mono text-[10px]">
                        <span
                          className={
                            r.m === "GET"
                              ? "text-emerald-600"
                              : "text-violet-600"
                          }
                        >
                          {r.m}
                        </span>
                      </td>
                      <td className="px-3 py-2 font-mono">{r.p}</td>
                      <td className="px-3 py-2">
                        <div className="flex flex-wrap gap-1">
                          {r.s.map((sc) => (
                            <code
                              key={sc}
                              className="rounded bg-muted px-1.5 py-0.5 font-mono text-[10px]"
                            >
                              {sc}
                            </code>
                          ))}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="mt-2 text-[11px] text-muted-foreground">
              Full OpenAPI spec:{" "}
              <a
                href={`${API_URL}/openapi.json`}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-primary hover:underline"
              >
                {API_URL}/openapi.json
                <ExternalLink className="h-2.5 w-2.5" />
              </a>
              .
            </p>
          </section>

          {/* Snippets */}
          <section>
            <h2 className="mb-3 text-sm font-semibold">Quickstart</h2>
            <Tabs defaultValue="curl">
              <TabsList>
                <TabsTrigger value="curl">cURL</TabsTrigger>
                <TabsTrigger value="python">Python</TabsTrigger>
                <TabsTrigger value="js">JavaScript</TabsTrigger>
              </TabsList>

              <TabsContent value="curl" className="mt-3 space-y-3">
                <ConfigSnippet
                  template={CURL_LIST}
                  vars={vars}
                  language="bash"
                  title="List your agents"
                />
                <ConfigSnippet
                  template={CURL_CHAT}
                  vars={vars}
                  language="bash"
                  title="Sync chat (one shot)"
                />
                <ConfigSnippet
                  template={CURL_STREAM}
                  vars={vars}
                  language="bash"
                  title="SSE stream"
                />
              </TabsContent>

              <TabsContent value="python" className="mt-3">
                <ConfigSnippet
                  template={PY_CODE}
                  vars={vars}
                  language="python"
                  title="Python — httpx"
                />
                <p className="mt-2 text-[11px] text-muted-foreground">
                  Dependencies: <code className="rounded bg-muted px-1 font-mono">pip install httpx</code>
                </p>
              </TabsContent>

              <TabsContent value="js" className="mt-3">
                <ConfigSnippet
                  template={JS_CODE}
                  vars={vars}
                  language="javascript"
                  title="JavaScript — fetch (Node 18+ / browser)"
                />
              </TabsContent>
            </Tabs>
          </section>

          {/* Rate limit notes */}
          <section className="rounded-lg border border-border bg-muted/30 p-4 text-xs">
            <h3 className="mb-2 font-semibold">Rate limits & errors</h3>
            <ul className="space-y-1 text-muted-foreground">
              <li>
                Default <strong>60 req/min/token</strong>. Server trả{" "}
                <code className="rounded bg-muted px-1 font-mono">429</code> với
                header <code className="rounded bg-muted px-1 font-mono">Retry-After</code>{" "}
                khi exceed.
              </li>
              <li>
                Token thiếu scope cần thiết →{" "}
                <code className="rounded bg-muted px-1 font-mono">403 Forbidden</code>
                . Kiểm tra cột "Required scopes" ở bảng trên.
              </li>
              <li>
                Token revoke / expire →{" "}
                <code className="rounded bg-muted px-1 font-mono">401 Unauthorized</code>
                . Tạo token mới và update env.
              </li>
              <li>
                Agent thiếu credential cho LLM provider →{" "}
                <code className="rounded bg-muted px-1 font-mono">400</code> với
                message giải thích. Mở agent editor connect credential rồi thử lại.
              </li>
            </ul>
          </section>

          <CodeBlockCopy
            code="✓ Sẵn sàng. Test bất kỳ snippet nào ở trên với token + agent ID thật."
            title="Done"
            className="border-emerald-500/30 bg-emerald-500/5"
          />
        </div>
      </div>
    </div>
  );
}
