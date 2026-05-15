"use client";

import { useEffect, useMemo, useState } from "react";
import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import {
  Copy,
  Eye,
  EyeOff,
  Loader2,
  Plus,
  ShieldCheck,
  Sparkles,
  Trash2,
} from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { billingService } from "@/lib/api/billingService";
import { organizationsService } from "@/lib/api/organizationsService";
import {
  type SCIMTokenCreated,
  type SSOConfig,
  type SSOConfigPayload,
  securityService,
} from "@/lib/api/securityService";
import { useActiveOrg } from "@/features/organizations/components/OrgLayout";
import {
  SettingsCard,
  SettingsStack,
} from "@/features/settings/components/SettingsPrimitives";
import { cn } from "@/lib/utils";

/**
 * Org → Security tab.
 *
 * Four sections, each behind a plan-feature gate so the FE never
 * shows config for an entitlement the org can't enable yet:
 *   A. MFA enforcement (PATCH /api/organizations/{id}.settings)
 *   B. Workspace IP allowlist (CIDR rules per workspace)
 *   C. SSO / SAML configuration (OIDC upsert; SAML deferred BE-side)
 *   D. SCIM bearer tokens (mint / list / revoke)
 *
 * Feature flags resolve via ``billingService.getSubscription()`` →
 * ``subscription.plan.features``. Per the active config the SSO flag
 * is True on every tier; SCIM + IP allowlist are Enterprise-only.
 */
export default function OrgSecurityPage() {
  const { org, isLoading } = useActiveOrg();
  const billingQ = useQuery({
    queryKey: ["billing", "subscription"],
    queryFn: () => billingService.getSubscription(),
    staleTime: 60_000,
  });

  if (isLoading || !org) return <PageSpinner />;

  const features = billingQ.data?.subscription.plan.features ?? {};
  const ssoEnabled = !!features.sso;
  const scimEnabled = !!features.scim;
  const ipEnabled = !!features.ip_allowlist;

  const canManage = org.role === "owner" || org.role === "admin";

  return (
    <div className="mx-auto max-w-3xl px-6 py-10 lg:px-8">
      <header className="border-b border-border pb-6">
        <h1 className="text-2xl font-bold tracking-tight">Security</h1>
        <p className="mt-1 max-w-2xl text-xs text-muted-foreground">
          Org-wide MFA policy, SSO, SCIM provisioning, và IP allowlist cho từng
          workspace. Một số tính năng cần plan Enterprise.
        </p>
      </header>

      <SettingsStack>
        <MfaSection orgId={org.id} canManage={canManage} />

        {ssoEnabled ? (
          <SSOSection orgId={org.id} canManage={canManage} />
        ) : (
          <UpgradeSection
            title="SSO / SAML"
            description="Cấu hình OIDC / SAML để team đăng nhập qua IdP. Hỗ trợ JIT provisioning."
          />
        )}

        {scimEnabled ? (
          <SCIMSection orgId={org.id} canManage={canManage} />
        ) : (
          <UpgradeSection
            title="SCIM provisioning"
            description="Cấp/thu hồi quyền tự động qua SCIM 2.0 từ IdP (Okta, Azure AD, OneLogin…)."
          />
        )}

        {ipEnabled ? (
          <IPAllowlistSection orgId={org.id} canManage={canManage} />
        ) : (
          <UpgradeSection
            title="IP allowlist"
            description="Giới hạn truy cập workspace theo CIDR range. Áp dụng cho mọi request, không chỉ login."
          />
        )}
      </SettingsStack>
    </div>
  );
}

/* ─── A. MFA enforcement ───────────────────────────────────────── */

function MfaSection({
  orgId,
  canManage,
}: {
  orgId: string;
  canManage: boolean;
}) {
  const qc = useQueryClient();
  // The ``settings`` blob lives on the org detail endpoint; the list
  // endpoint elides it. Fetch separately, scoped to this org.
  const detailQ = useQuery({
    queryKey: ["organizations", orgId, "detail"],
    queryFn: () => organizationsService.get(orgId),
    staleTime: 30_000,
  });

  const currentValue = !!(detailQ.data?.settings as { mfa_required?: boolean } | undefined)
    ?.mfa_required;

  const toggle = useMutation({
    mutationFn: (next: boolean) =>
      organizationsService.update(orgId, {
        settings: { ...(detailQ.data?.settings ?? {}), mfa_required: next },
      }),
    onSuccess: (updated) => {
      const nowOn = !!(updated.settings as { mfa_required?: boolean } | undefined)
        ?.mfa_required;
      toast.success(
        nowOn ? "MFA enforcement enabled" : "MFA enforcement disabled",
      );
      qc.invalidateQueries({ queryKey: ["organizations", orgId, "detail"] });
    },
    onError: (e) => toast.error(extractMsg(e)),
  });

  return (
    <SettingsCard
      title="MFA enforcement"
      description="Buộc mọi thành viên org bật 2FA. Bật cờ này sẽ chặn login bằng password không kèm MFA cho đến khi user enroll."
    >
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <Label htmlFor="org-mfa-required" className="text-xs font-medium">
            Require all org members to enable MFA
          </Label>
          <p className="mt-1 text-[11px] text-muted-foreground">
            Áp dụng cho mọi workspace trong org. Member chưa bật MFA sẽ bị buộc
            enroll ở lần login kế tiếp.
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {(detailQ.isLoading || toggle.isPending) && (
            <Loader2 className="h-3.5 w-3.5 animate-spin text-muted-foreground" />
          )}
          <Switch
            id="org-mfa-required"
            checked={currentValue}
            disabled={
              !canManage || detailQ.isLoading || toggle.isPending
            }
            onCheckedChange={(next) => toggle.mutate(next)}
          />
        </div>
      </div>
      {!canManage && (
        <p className="mt-3 text-[10px] text-muted-foreground">
          Chỉ owner/admin chỉnh được policy này.
        </p>
      )}
    </SettingsCard>
  );
}

/* ─── B. IP allowlist (workspace-scoped) ───────────────────────── */

function IPAllowlistSection({
  orgId,
  canManage,
}: {
  orgId: string;
  canManage: boolean;
}) {
  // List every workspace under the org — IP rules live per-workspace
  // on the BE, but the management surface lives here so an org-admin
  // can configure them all from one place.
  const workspacesQ = useQuery({
    queryKey: ["organizations", orgId, "workspaces"],
    queryFn: () => organizationsService.listWorkspaces(orgId),
    staleTime: 60_000,
  });

  const workspaces = useMemo(
    () => (workspacesQ.data ?? []).filter((w) => !w.is_personal),
    [workspacesQ.data],
  );

  const [selectedWsId, setSelectedWsId] = useState<string>("");
  useEffect(() => {
    if (!selectedWsId && workspaces.length > 0) {
      setSelectedWsId(workspaces[0].id);
    }
  }, [workspaces, selectedWsId]);

  return (
    <SettingsCard
      title="IP allowlist"
      description="Mỗi workspace có rule CIDR riêng. Khi có rule, mọi request từ IP nằm ngoài range sẽ bị 403."
    >
      {workspacesQ.isLoading ? (
        <Spinner />
      ) : workspaces.length === 0 ? (
        <Empty>Org chưa có team workspace nào.</Empty>
      ) : (
        <>
          <div className="space-y-1.5">
            <Label htmlFor="ip-ws-picker" className="text-[11px]">
              Workspace
            </Label>
            <select
              id="ip-ws-picker"
              value={selectedWsId}
              onChange={(e) => setSelectedWsId(e.target.value)}
              className="h-9 w-full rounded-md border border-border bg-background px-2 text-xs"
            >
              {workspaces.map((w) => (
                <option key={w.id} value={w.id}>
                  {w.name}
                </option>
              ))}
            </select>
          </div>
          {selectedWsId && (
            <IPRulesForWorkspace
              workspaceId={selectedWsId}
              canManage={canManage}
            />
          )}
        </>
      )}
    </SettingsCard>
  );
}

function IPRulesForWorkspace({
  workspaceId,
  canManage,
}: {
  workspaceId: string;
  canManage: boolean;
}) {
  const qc = useQueryClient();
  const rulesQ = useQuery({
    queryKey: ["workspaces", workspaceId, "ip-rules"],
    queryFn: () => securityService.listIPRules(workspaceId),
  });

  const [cidr, setCidr] = useState("");
  const [description, setDescription] = useState("");

  const create = useMutation({
    mutationFn: () =>
      securityService.createIPRule(workspaceId, {
        cidr: cidr.trim(),
        description: description.trim() || null,
      }),
    onSuccess: () => {
      toast.success("IP rule added");
      setCidr("");
      setDescription("");
      qc.invalidateQueries({
        queryKey: ["workspaces", workspaceId, "ip-rules"],
      });
    },
    onError: (e) => toast.error(extractMsg(e)),
  });

  const remove = useMutation({
    mutationFn: (id: string) => securityService.deleteIPRule(workspaceId, id),
    onSuccess: () => {
      toast.success("IP rule removed");
      qc.invalidateQueries({
        queryKey: ["workspaces", workspaceId, "ip-rules"],
      });
    },
    onError: (e) => toast.error(extractMsg(e)),
  });

  return (
    <div className="mt-5 space-y-4 border-t border-border pt-5">
      {canManage && (
        <div className="grid gap-2 sm:grid-cols-[1fr_1.5fr_auto]">
          <div className="space-y-1">
            <Label htmlFor="ip-cidr" className="text-[10px] uppercase tracking-wider text-muted-foreground">
              CIDR
            </Label>
            <Input
              id="ip-cidr"
              value={cidr}
              onChange={(e) => setCidr(e.target.value)}
              placeholder="10.0.0.0/24"
              className="h-8 font-mono text-xs"
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="ip-desc" className="text-[10px] uppercase tracking-wider text-muted-foreground">
              Description
            </Label>
            <Input
              id="ip-desc"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="HQ office"
              className="h-8 text-xs"
            />
          </div>
          <div className="flex items-end">
            <Button
              size="sm"
              onClick={() => create.mutate()}
              disabled={!cidr.trim() || create.isPending}
            >
              {create.isPending ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <>
                  <Plus className="mr-1.5 h-3.5 w-3.5" />
                  Add
                </>
              )}
            </Button>
          </div>
        </div>
      )}

      {rulesQ.isLoading ? (
        <Spinner />
      ) : (rulesQ.data ?? []).length === 0 ? (
        <Empty>Chưa có rule — workspace mở cho mọi IP.</Empty>
      ) : (
        <ul className="divide-y divide-border rounded-lg border border-border">
          {(rulesQ.data ?? []).map((r) => (
            <li
              key={r.id}
              className="flex items-center gap-3 px-4 py-2.5 text-xs"
            >
              <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-[11px]">
                {r.cidr}
              </code>
              <span className="min-w-0 flex-1 truncate text-muted-foreground">
                {r.description || "—"}
              </span>
              {canManage && (
                <Button
                  variant="ghost"
                  size="icon-sm"
                  onClick={() => remove.mutate(r.id)}
                  disabled={remove.isPending}
                  className="text-muted-foreground hover:text-destructive"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/* ─── C. SSO / SAML ────────────────────────────────────────────── */

const EMPTY_OIDC_FORM = {
  display_name: "",
  is_active: false,
  jit_provisioning: true,
  default_role: "editor",
  oidc_issuer: "",
  oidc_client_id: "",
  oidc_client_secret: "",
  oidc_scopes: "openid email profile",
} as const;

type OIDCForm = {
  display_name: string;
  is_active: boolean;
  jit_provisioning: boolean;
  default_role: string;
  oidc_issuer: string;
  oidc_client_id: string;
  oidc_client_secret: string;
  oidc_scopes: string;
};

function SSOSection({
  orgId,
  canManage,
}: {
  orgId: string;
  canManage: boolean;
}) {
  const qc = useQueryClient();
  const configsQ = useQuery({
    queryKey: ["organizations", orgId, "sso"],
    queryFn: () => securityService.listSSOConfigs(orgId),
  });

  const existing: SSOConfig | undefined = (configsQ.data ?? []).find(
    (c) => c.provider === "oidc",
  );

  const [form, setForm] = useState<OIDCForm>({ ...EMPTY_OIDC_FORM });
  const [showSecret, setShowSecret] = useState(false);

  // Re-seed when the server config refetches or initially loads. The
  // secret is intentionally NOT round-tripped from the BE; an empty
  // string means "keep existing on save".
  useEffect(() => {
    if (existing) {
      setForm({
        display_name: existing.display_name,
        is_active: existing.is_active,
        jit_provisioning: existing.jit_provisioning,
        default_role: existing.default_role,
        oidc_issuer: existing.oidc_issuer ?? "",
        oidc_client_id: existing.oidc_client_id ?? "",
        oidc_client_secret: "",
        oidc_scopes: (existing.oidc_scopes ?? ["openid", "email", "profile"]).join(
          " ",
        ),
      });
    }
  }, [existing]);

  const save = useMutation({
    mutationFn: () => {
      const payload: SSOConfigPayload = {
        provider: "oidc",
        display_name: form.display_name.trim() || "OIDC",
        is_active: form.is_active,
        jit_provisioning: form.jit_provisioning,
        default_role: form.default_role,
        oidc_issuer: form.oidc_issuer.trim() || null,
        oidc_client_id: form.oidc_client_id.trim() || null,
        oidc_scopes: form.oidc_scopes.trim().split(/\s+/).filter(Boolean),
      };
      // Only send the secret when the user typed one — empty means
      // "leave the encrypted value untouched on the BE".
      if (form.oidc_client_secret.trim()) {
        payload.oidc_client_secret = form.oidc_client_secret;
      }
      return securityService.upsertSSOConfig(orgId, payload);
    },
    onSuccess: () => {
      toast.success("SSO config saved");
      setForm((f) => ({ ...f, oidc_client_secret: "" }));
      setShowSecret(false);
      qc.invalidateQueries({ queryKey: ["organizations", orgId, "sso"] });
    },
    onError: (e) => toast.error(extractMsg(e)),
  });

  const remove = useMutation({
    mutationFn: () => securityService.deleteSSOConfig(orgId, "oidc"),
    onSuccess: () => {
      toast.success("SSO config removed");
      setForm({ ...EMPTY_OIDC_FORM });
      qc.invalidateQueries({ queryKey: ["organizations", orgId, "sso"] });
    },
    onError: (e) => toast.error(extractMsg(e)),
  });

  const canSave =
    !!form.oidc_issuer.trim() &&
    !!form.oidc_client_id.trim() &&
    // Either updating an existing row (no secret needed) or creating
    // a new one (secret is required).
    (!!existing || !!form.oidc_client_secret.trim());

  return (
    <SettingsCard
      title="SSO — OpenID Connect"
      description="Cấu hình OIDC provider. Sau khi bật, login URL sẽ là /api/sso/oidc/{org_slug}/login."
    >
      {configsQ.isLoading ? (
        <Spinner />
      ) : (
        <div className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Display name" htmlFor="oidc-name">
              <Input
                id="oidc-name"
                value={form.display_name}
                onChange={(e) =>
                  setForm({ ...form, display_name: e.target.value })
                }
                placeholder="Acme Okta"
                disabled={!canManage}
              />
            </Field>
            <Field label="Default role" htmlFor="oidc-role">
              <select
                id="oidc-role"
                value={form.default_role}
                onChange={(e) =>
                  setForm({ ...form, default_role: e.target.value })
                }
                disabled={!canManage}
                className="h-9 w-full rounded-md border border-border bg-background px-2 text-xs"
              >
                {["viewer", "editor", "admin"].map((r) => (
                  <option key={r} value={r}>
                    {r}
                  </option>
                ))}
              </select>
            </Field>
          </div>

          <Field
            label="Issuer URL"
            htmlFor="oidc-issuer"
            hint="OIDC discovery document = {issuer}/.well-known/openid-configuration."
          >
            <Input
              id="oidc-issuer"
              value={form.oidc_issuer}
              onChange={(e) =>
                setForm({ ...form, oidc_issuer: e.target.value })
              }
              placeholder="https://example.okta.com"
              disabled={!canManage}
              className="font-mono text-xs"
            />
          </Field>

          <Field label="Client ID" htmlFor="oidc-client-id">
            <Input
              id="oidc-client-id"
              value={form.oidc_client_id}
              onChange={(e) =>
                setForm({ ...form, oidc_client_id: e.target.value })
              }
              disabled={!canManage}
              className="font-mono text-xs"
            />
          </Field>

          <Field
            label="Client secret"
            htmlFor="oidc-client-secret"
            hint={
              existing
                ? "Để trống = giữ secret cũ. Nhập mới để overwrite."
                : "Required khi tạo mới."
            }
          >
            <div className="relative">
              <Input
                id="oidc-client-secret"
                type={showSecret ? "text" : "password"}
                value={form.oidc_client_secret}
                onChange={(e) =>
                  setForm({ ...form, oidc_client_secret: e.target.value })
                }
                placeholder={existing ? "••••••••" : ""}
                disabled={!canManage}
                className="pr-10 font-mono text-xs"
              />
              <button
                type="button"
                onClick={() => setShowSecret((v) => !v)}
                disabled={!canManage}
                className="absolute right-2 top-1/2 -translate-y-1/2 rounded-md p-1 text-muted-foreground hover:text-foreground"
                aria-label={showSecret ? "Hide secret" : "Show secret"}
              >
                {showSecret ? (
                  <EyeOff className="h-3.5 w-3.5" />
                ) : (
                  <Eye className="h-3.5 w-3.5" />
                )}
              </button>
            </div>
          </Field>

          <Field
            label="Scopes"
            htmlFor="oidc-scopes"
            hint="Cách nhau bằng dấu cách. Mặc định: openid email profile."
          >
            <Input
              id="oidc-scopes"
              value={form.oidc_scopes}
              onChange={(e) =>
                setForm({ ...form, oidc_scopes: e.target.value })
              }
              disabled={!canManage}
              className="font-mono text-xs"
            />
          </Field>

          <div className="grid gap-3 sm:grid-cols-2">
            <ToggleRow
              id="oidc-active"
              label="Active"
              hint="Khi tắt, login URL trả 404 — dùng để pause SSO mà không xoá config."
              checked={form.is_active}
              onCheckedChange={(v) => setForm({ ...form, is_active: v })}
              disabled={!canManage}
            />
            <ToggleRow
              id="oidc-jit"
              label="JIT provisioning"
              hint="Tự tạo user khi login lần đầu. Tắt nếu chỉ cho member đã invite."
              checked={form.jit_provisioning}
              onCheckedChange={(v) =>
                setForm({ ...form, jit_provisioning: v })
              }
              disabled={!canManage}
            />
          </div>

          <div className="flex items-center justify-between gap-2 border-t border-border pt-4">
            {existing ? (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  if (
                    window.confirm(
                      "Remove the OIDC config? Active SSO logins will start failing immediately.",
                    )
                  ) {
                    remove.mutate();
                  }
                }}
                disabled={!canManage || remove.isPending}
                className="text-muted-foreground hover:text-destructive"
              >
                {remove.isPending ? (
                  <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
                ) : (
                  <Trash2 className="mr-1.5 h-3.5 w-3.5" />
                )}
                Delete
              </Button>
            ) : (
              <span />
            )}
            <Button
              size="sm"
              onClick={() => save.mutate()}
              disabled={!canManage || !canSave || save.isPending}
            >
              {save.isPending ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : existing ? (
                "Save"
              ) : (
                "Create"
              )}
            </Button>
          </div>

          <div className="rounded-md border border-dashed border-border bg-muted/30 p-3 text-[10px] text-muted-foreground">
            <strong className="text-foreground">SAML coming soon</strong> — BE
            schema có cột SAML nhưng handler chưa wire. Form sẽ mở khi BE ship
            SAML callback.
          </div>
        </div>
      )}
    </SettingsCard>
  );
}

/* ─── D. SCIM tokens ───────────────────────────────────────────── */

function SCIMSection({
  orgId,
  canManage,
}: {
  orgId: string;
  canManage: boolean;
}) {
  const qc = useQueryClient();
  const tokensQ = useQuery({
    queryKey: ["organizations", orgId, "scim-tokens"],
    queryFn: () => securityService.listSCIMTokens(orgId),
  });

  const [dialogOpen, setDialogOpen] = useState(false);
  const [justMinted, setJustMinted] = useState<SCIMTokenCreated | null>(null);

  const create = useMutation({
    mutationFn: (name: string) =>
      securityService.createSCIMToken(orgId, { name }),
    onSuccess: (data) => {
      setJustMinted(data);
      setDialogOpen(false);
      qc.invalidateQueries({
        queryKey: ["organizations", orgId, "scim-tokens"],
      });
    },
    onError: (e) => toast.error(extractMsg(e)),
  });

  const revoke = useMutation({
    mutationFn: (tokenId: string) =>
      securityService.revokeSCIMToken(orgId, tokenId),
    onSuccess: () => {
      toast.success("Token revoked");
      qc.invalidateQueries({
        queryKey: ["organizations", orgId, "scim-tokens"],
      });
    },
    onError: (e) => toast.error(extractMsg(e)),
  });

  const tokens = tokensQ.data ?? [];
  const active = tokens.filter((t) => !t.revoked_at);

  return (
    <SettingsCard
      title="SCIM tokens"
      description="Bearer token cho IdP push user/de-provision qua SCIM 2.0. Endpoint: /api/scim/v2/Users."
      action={
        canManage && (
          <Button size="sm" onClick={() => setDialogOpen(true)}>
            <Plus className="mr-1.5 h-3.5 w-3.5" />
            Generate token
          </Button>
        )
      }
    >
      {tokensQ.isLoading ? (
        <Spinner />
      ) : active.length === 0 ? (
        <Empty>Chưa có active SCIM token.</Empty>
      ) : (
        <ul className="divide-y divide-border rounded-lg border border-border">
          {active.map((t) => (
            <li
              key={t.id}
              className="flex items-center gap-3 px-4 py-2.5 text-xs"
            >
              <div className="min-w-0 flex-1">
                <div className="truncate font-medium">{t.name}</div>
                <div className="flex flex-wrap items-center gap-1.5 text-[10px] text-muted-foreground">
                  <span>Created {formatDate(t.created_at)}</span>
                  <span>·</span>
                  <span>
                    Last used{" "}
                    {t.last_used_at ? formatDate(t.last_used_at) : "never"}
                  </span>
                  {t.expires_at && (
                    <>
                      <span>·</span>
                      <span>Expires {formatDate(t.expires_at)}</span>
                    </>
                  )}
                </div>
              </div>
              {canManage && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    if (
                      window.confirm(
                        `Revoke "${t.name}"? IdP push will fail until you mint a new token.`,
                      )
                    ) {
                      revoke.mutate(t.id);
                    }
                  }}
                  disabled={revoke.isPending}
                  className="text-muted-foreground hover:text-destructive"
                >
                  Revoke
                </Button>
              )}
            </li>
          ))}
        </ul>
      )}

      <CreateSCIMDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        onCreate={(name) => create.mutate(name)}
        loading={create.isPending}
      />
      <ShowSecretDialog
        token={justMinted}
        onClose={() => setJustMinted(null)}
      />
    </SettingsCard>
  );
}

function CreateSCIMDialog({
  open,
  onOpenChange,
  onCreate,
  loading,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  onCreate: (name: string) => void;
  loading: boolean;
}) {
  const [name, setName] = useState("");
  if (!open) return null;
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      onClick={() => onOpenChange(false)}
    >
      <div
        className="w-full max-w-md rounded-lg border border-border bg-card p-5"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-base font-semibold">Generate SCIM token</h2>
        <p className="mt-1 text-[11px] text-muted-foreground">
          Đặt tên gợi nhớ (e.g. provider/env). Token sẽ hiện duy nhất 1 lần ở
          dialog tiếp theo — sao chép trước khi đóng.
        </p>
        <div className="mt-4 space-y-1">
          <Label htmlFor="scim-token-name" className="text-[11px]">
            Name
          </Label>
          <Input
            id="scim-token-name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Okta production"
            autoFocus
          />
        </div>
        <div className="mt-5 flex justify-end gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onOpenChange(false)}
            disabled={loading}
          >
            Cancel
          </Button>
          <Button
            size="sm"
            disabled={!name.trim() || loading}
            onClick={() => onCreate(name.trim())}
          >
            {loading ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              "Generate"
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}

function ShowSecretDialog({
  token,
  onClose,
}: {
  token: SCIMTokenCreated | null;
  onClose: () => void;
}) {
  if (!token) return null;
  const copy = () => {
    navigator.clipboard
      .writeText(token.plaintext)
      .then(() => toast.success("Copied to clipboard"))
      .catch(() => toast.error("Copy failed — select + copy manually"));
  };
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      onClick={onClose}
    >
      <div
        className="w-full max-w-lg rounded-lg border border-border bg-card p-5"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="flex items-center gap-2 text-base font-semibold">
          <ShieldCheck className="h-4 w-4 text-primary" />
          Save this token now
        </h2>
        <p className="mt-1 text-[11px] text-muted-foreground">
          Token chỉ hiển thị 1 lần duy nhất. Sau khi đóng dialog, không có cách
          nào xem lại — phải revoke + tạo mới nếu mất.
        </p>
        <div className="mt-4 rounded-md border border-border bg-muted/40 p-3">
          <code className="block break-all font-mono text-[11px]">
            {token.plaintext}
          </code>
        </div>
        <div className="mt-4 flex justify-end gap-2">
          <Button variant="ghost" size="sm" onClick={onClose}>
            Done
          </Button>
          <Button size="sm" onClick={copy}>
            <Copy className="mr-1.5 h-3.5 w-3.5" />
            Copy
          </Button>
        </div>
      </div>
    </div>
  );
}

/* ─── Upgrade CTA placeholder ──────────────────────────────────── */

function UpgradeSection({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <SettingsCard
      title={title}
      description={description}
      className="border-dashed"
    >
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Sparkles className="h-3.5 w-3.5 text-amber-500" />
          <span>
            Tính năng này nằm trong plan Enterprise.{" "}
            <a
              href="/org/billing"
              className="font-medium text-primary hover:underline"
            >
              Upgrade →
            </a>
          </span>
        </div>
        <Badge variant="outline" className="text-[10px]">
          Enterprise
        </Badge>
      </div>
    </SettingsCard>
  );
}

/* ─── Small helpers ────────────────────────────────────────────── */

function Field({
  label,
  hint,
  htmlFor,
  children,
}: {
  label: string;
  hint?: string;
  htmlFor?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <Label htmlFor={htmlFor} className="text-[11px]">
        {label}
      </Label>
      {children}
      {hint && <p className="text-[10px] text-muted-foreground/70">{hint}</p>}
    </div>
  );
}

function ToggleRow({
  id,
  label,
  hint,
  checked,
  onCheckedChange,
  disabled,
}: {
  id: string;
  label: string;
  hint?: string;
  checked: boolean;
  onCheckedChange: (v: boolean) => void;
  disabled?: boolean;
}) {
  return (
    <div className="flex items-start justify-between gap-3 rounded-md border border-border bg-muted/20 p-3">
      <div className="min-w-0 flex-1">
        <Label htmlFor={id} className="text-xs font-medium">
          {label}
        </Label>
        {hint && (
          <p className="mt-0.5 text-[10px] text-muted-foreground">{hint}</p>
        )}
      </div>
      <Switch
        id={id}
        checked={checked}
        onCheckedChange={onCheckedChange}
        disabled={disabled}
      />
    </div>
  );
}

function Spinner() {
  return (
    <div className="flex h-20 items-center justify-center">
      <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
    </div>
  );
}

function PageSpinner() {
  return (
    <div className="flex h-32 items-center justify-center">
      <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
    </div>
  );
}

function Empty({ children }: { children: React.ReactNode }) {
  return (
    <div
      className={cn(
        "rounded-md border border-dashed border-border p-6 text-center text-xs text-muted-foreground",
      )}
    >
      {children}
    </div>
  );
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch {
    return iso;
  }
}

function extractMsg(err: unknown): string {
  const anyErr = err as {
    response?: { data?: { detail?: string | object } };
    message?: string;
  };
  const detail = anyErr?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (detail && typeof detail === "object") return JSON.stringify(detail);
  return anyErr?.message ?? "Request failed";
}
