"use client";

import { useEffect, useState } from "react";
import { Globe, Lock } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { MonacoEditor } from "../MonacoEditor";
import { KeyValueTable } from "./KeyValueTable";
import { type KVPair, newKvId, objectToKvs } from "../../utils";

const HTTP_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD"] as const;
type HttpMethod = (typeof HTTP_METHODS)[number];

const AUTH_TYPES = [
  { value: "none", label: "No Auth" },
  { value: "bearer", label: "Bearer Token" },
  { value: "api_key", label: "API Key (header)" },
  { value: "basic", label: "Basic Auth" },
] as const;
type AuthType = "none" | "bearer" | "api_key" | "basic";

export interface HttpConfig {
  method: HttpMethod;
  url: string;
  headers: Record<string, string>;
  params: Record<string, string>;
  body_template: string;
  auth_type: AuthType;
  auth_token?: string;
  auth_key_header?: string;
  auth_key_value?: string;
  auth_username?: string;
  auth_password?: string;
}

function defaultHttpConfig(): HttpConfig {
  return {
    method: "GET",
    url: "",
    headers: {},
    params: {},
    body_template: "",
    auth_type: "none",
  };
}

function parseConfig(raw: Record<string, unknown>): HttpConfig {
  const defaults = defaultHttpConfig();
  return {
    method: (raw.method as HttpMethod) ?? defaults.method,
    url: (raw.url as string) ?? defaults.url,
    headers: (raw.headers as Record<string, string>) ?? defaults.headers,
    params: (raw.params as Record<string, string>) ?? defaults.params,
    body_template: (raw.body_template as string) ?? defaults.body_template,
    auth_type: (raw.auth_type as AuthType) ?? defaults.auth_type,
    auth_token: raw.auth_token as string | undefined,
    auth_key_header: raw.auth_key_header as string | undefined,
    auth_key_value: raw.auth_key_value as string | undefined,
    auth_username: raw.auth_username as string | undefined,
    auth_password: raw.auth_password as string | undefined,
  };
}

interface HttpConfigFormProps {
  value: Record<string, unknown>;
  onChange: (value: Record<string, unknown>) => void;
}

export function HttpConfigForm({ value, onChange }: HttpConfigFormProps) {
  const cfg = parseConfig(value);
  const [headers, setHeaders] = useState<KVPair[]>(() =>
    objectToKvs(cfg.headers).length
      ? objectToKvs(cfg.headers)
      : [{ id: newKvId(), key: "", value: "", enabled: true }]
  );
  const [params, setParams] = useState<KVPair[]>(() =>
    objectToKvs(cfg.params).length
      ? objectToKvs(cfg.params)
      : [{ id: newKvId(), key: "", value: "", enabled: true }]
  );

  const buildConfig = (
    patch: Partial<HttpConfig>,
    hdrs: KVPair[] = headers,
    pms: KVPair[] = params
  ) => {
    const updated = { ...cfg, ...patch };
    const headersObj: Record<string, string> = {};
    for (const h of hdrs) {
      if (h.enabled && h.key.trim()) headersObj[h.key.trim()] = h.value;
    }
    const paramsObj: Record<string, string> = {};
    for (const p of pms) {
      if (p.enabled && p.key.trim()) paramsObj[p.key.trim()] = p.value;
    }
    onChange({ ...updated, headers: headersObj, params: paramsObj });
  };

  const update = (patch: Partial<HttpConfig>) => buildConfig(patch);

  const handleHeaders = (newKvs: KVPair[]) => {
    setHeaders(newKvs);
    buildConfig({}, newKvs, params);
  };

  const handleParams = (newKvs: KVPair[]) => {
    setParams(newKvs);
    buildConfig({}, headers, newKvs);
  };

  const showBody = ["POST", "PUT", "PATCH"].includes(cfg.method);

  return (
    <div className="space-y-4">
      {/* Method + URL */}
      <div className="flex gap-2">
        <Select value={cfg.method} onValueChange={(v) => update({ method: v as HttpMethod })}>
          <SelectTrigger className="h-9 w-28 shrink-0 font-mono text-xs">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {HTTP_METHODS.map((m) => (
              <SelectItem key={m} value={m} className="font-mono text-xs">
                {m}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <div className="relative flex-1">
          <Globe className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
          <Input
            className="h-9 pl-8 font-mono text-xs"
            placeholder="https://api.example.com/v1/users/{user_id}"
            value={cfg.url}
            onChange={(e) => update({ url: e.target.value })}
          />
        </div>
      </div>

      <Tabs defaultValue="headers">
        <TabsList className="h-8">
          <TabsTrigger value="headers" className="h-7 text-xs">
            Headers
          </TabsTrigger>
          <TabsTrigger value="params" className="h-7 text-xs">
            Query Params
          </TabsTrigger>
          {showBody && (
            <TabsTrigger value="body" className="h-7 text-xs">
              Body
            </TabsTrigger>
          )}
          <TabsTrigger value="auth" className="h-7 text-xs">
            Auth
          </TabsTrigger>
        </TabsList>

        <TabsContent value="headers" className="mt-3">
          <KeyValueTable
            value={headers}
            onChange={handleHeaders}
            keyPlaceholder="Header-Name"
            valuePlaceholder="Value or {variable}"
          />
        </TabsContent>

        <TabsContent value="params" className="mt-3">
          <KeyValueTable
            value={params}
            onChange={handleParams}
            keyPlaceholder="param_name"
            valuePlaceholder="value or {variable}"
          />
        </TabsContent>

        {showBody && (
          <TabsContent value="body" className="mt-3 space-y-2">
            <p className="text-xs text-muted-foreground">
              JSON body template. Use <code className="rounded bg-muted px-1">{"{variable}"}</code>{" "}
              for dynamic values.
            </p>
            <MonacoEditor
              language="json"
              height={200}
              value={cfg.body_template}
              onChange={(v) => update({ body_template: v })}
            />
          </TabsContent>
        )}

        <TabsContent value="auth" className="mt-3 space-y-4">
          <div className="space-y-1.5">
            <Label className="text-xs text-muted-foreground">Auth type</Label>
            <Select
              value={cfg.auth_type}
              onValueChange={(v) => update({ auth_type: v as AuthType })}
            >
              <SelectTrigger className="h-8 w-56 text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {AUTH_TYPES.map((a) => (
                  <SelectItem key={a.value} value={a.value} className="text-xs">
                    {a.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {cfg.auth_type === "bearer" && (
            <div className="space-y-1.5">
              <Label className="text-xs text-muted-foreground">Bearer Token</Label>
              <div className="relative">
                <Lock className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
                <Input
                  className="h-8 pl-8 font-mono text-xs"
                  placeholder="Use {token_variable} or paste static token"
                  value={cfg.auth_token ?? ""}
                  onChange={(e) => update({ auth_token: e.target.value })}
                />
              </div>
              <p className="text-[11px] text-muted-foreground">
                Stored as <code className="bg-muted px-1 rounded">Authorization: Bearer …</code> header at runtime.
              </p>
            </div>
          )}

          {cfg.auth_type === "api_key" && (
            <div className="space-y-3">
              <div className="space-y-1.5">
                <Label className="text-xs text-muted-foreground">Header name</Label>
                <Input
                  className="h-8 font-mono text-xs"
                  placeholder="X-API-Key"
                  value={cfg.auth_key_header ?? ""}
                  onChange={(e) => update({ auth_key_header: e.target.value })}
                />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs text-muted-foreground">API Key value</Label>
                <div className="relative">
                  <Lock className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
                  <Input
                    className="h-8 pl-8 font-mono text-xs"
                    placeholder="Use {api_key_variable} or paste key"
                    value={cfg.auth_key_value ?? ""}
                    onChange={(e) => update({ auth_key_value: e.target.value })}
                  />
                </div>
              </div>
            </div>
          )}

          {cfg.auth_type === "basic" && (
            <div className="space-y-3">
              <div className="space-y-1.5">
                <Label className="text-xs text-muted-foreground">Username</Label>
                <Input
                  className="h-8 font-mono text-xs"
                  placeholder="{username_variable}"
                  value={cfg.auth_username ?? ""}
                  onChange={(e) => update({ auth_username: e.target.value })}
                />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs text-muted-foreground">Password</Label>
                <div className="relative">
                  <Lock className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
                  <Input
                    className="h-8 pl-8 font-mono text-xs"
                    placeholder="{password_variable}"
                    value={cfg.auth_password ?? ""}
                    onChange={(e) => update({ auth_password: e.target.value })}
                  />
                </div>
              </div>
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
