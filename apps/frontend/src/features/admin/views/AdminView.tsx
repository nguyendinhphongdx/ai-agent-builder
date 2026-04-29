"use client";

import { useState } from "react";
import {
  BarChart3,
  ClipboardList,
  CreditCard,
  Loader2,
  ShieldAlert,
  Sparkles,
  Users,
} from "lucide-react";
import { useAuth } from "@/features/auth/hooks/useAuth";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { isStaff, type UserRole } from "../types";
import { hasRole } from "../types";
import { TemplatesTab } from "../components/TemplatesTab";
import { UsersTab } from "../components/UsersTab";
import { PurchasesTab } from "../components/PurchasesTab";
import { StatsTab } from "../components/StatsTab";
import { AuditTab } from "../components/AuditTab";

const TABS = [
  { id: "stats", label: "Stats", icon: BarChart3, minRole: "moderator" as UserRole },
  { id: "templates", label: "Templates", icon: Sparkles, minRole: "moderator" as UserRole },
  { id: "users", label: "Users", icon: Users, minRole: "support" as UserRole },
  { id: "purchases", label: "Purchases", icon: CreditCard, minRole: "support" as UserRole },
  { id: "audit", label: "Audit log", icon: ClipboardList, minRole: "moderator" as UserRole },
];

export function AdminView() {
  const { user, isLoading } = useAuth();
  const [tab, setTab] = useState("stats");

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const role = user?.role ?? "user";
  if (!isStaff(role)) {
    return (
      <div className="mx-auto flex min-h-[60vh] max-w-md items-center justify-center px-4">
        <div className="space-y-3 rounded-xl border border-border bg-card p-8 text-center">
          <ShieldAlert className="mx-auto h-10 w-10 text-red-500" />
          <h1 className="text-base font-semibold">Access denied</h1>
          <p className="text-xs text-muted-foreground">
            This page is for platform staff only.
          </p>
        </div>
      </div>
    );
  }

  const visibleTabs = TABS.filter((t) => hasRole(role, t.minRole));

  return (
    <div className="mx-auto max-w-7xl px-4 py-6">
      <header className="mb-6 flex items-end justify-between">
        <div>
          <h1 className="font-heading text-2xl font-semibold">Admin</h1>
          <p className="text-sm text-muted-foreground">
            Logged in as <span className="font-medium">{user?.email}</span> ({role})
          </p>
        </div>
      </header>

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList className="mb-6">
          {visibleTabs.map((t) => (
            <TabsTrigger key={t.id} value={t.id} className="gap-1.5">
              <t.icon className="h-3.5 w-3.5" />
              {t.label}
            </TabsTrigger>
          ))}
        </TabsList>

        <TabsContent value="stats">
          <StatsTab />
        </TabsContent>
        <TabsContent value="templates">
          <TemplatesTab />
        </TabsContent>
        {hasRole(role, "support") && (
          <TabsContent value="users">
            <UsersTab currentRole={role} />
          </TabsContent>
        )}
        {hasRole(role, "support") && (
          <TabsContent value="purchases">
            <PurchasesTab />
          </TabsContent>
        )}
        <TabsContent value="audit">
          <AuditTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}
