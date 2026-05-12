"use client";

import { useState } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  BookOpen,
  FileText,
  Loader2,
  Plug,
  Search,
  Settings,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { useKnowledgeBase } from "../hooks/useKnowledge";
import { ConnectorsTab } from "../components/connectors/ConnectorsTab";
import { DocumentsTab } from "../components/detail/DocumentsTab";
import { KBSettingsTab } from "../components/detail/KBSettingsTab";
import { RetrievalTestingTab } from "../components/detail/RetrievalTestingTab";

const TABS = [
  { id: "documents", label: "Documents", icon: FileText },
  { id: "connectors", label: "Connectors", icon: Plug },
  { id: "retrieval", label: "Retrieval Testing", icon: Search },
  { id: "settings", label: "Settings", icon: Settings },
] as const;

type TabId = (typeof TABS)[number]["id"];

interface KnowledgeDetailViewProps {
  kbId: string;
  initialTab?: TabId;
}

export function KnowledgeDetailView({ kbId, initialTab = "documents" }: KnowledgeDetailViewProps) {
  const [tab, setTab] = useState<TabId>(initialTab);
  const { data: kb, isLoading } = useKnowledgeBase(kbId);

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center text-muted-foreground">
        <Loader2 className="h-5 w-5 animate-spin" />
      </div>
    );
  }

  if (!kb) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
        Knowledge không tồn tại hoặc đã bị xoá.
      </div>
    );
  }

  return (
    <div className="flex h-full">
      {/* Left sidebar */}
      <aside className="flex w-64 shrink-0 flex-col border-r border-border bg-muted/30">
        <div className="px-4 pb-2 pt-4">
          <Link
            href="/knowledge"
            className="mb-3 inline-flex items-center gap-1.5 text-[11px] font-semibold tracking-wider text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft className="h-3 w-3" />
            KNOWLEDGE
          </Link>

          <div className="flex items-start gap-2.5">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-primary/25 bg-primary/10">
              <BookOpen className="h-4 w-4 text-primary" />
            </div>
            <div className="min-w-0">
              <h2 className="truncate text-sm font-semibold">{kb.name}</h2>
              <p className="mt-0.5 line-clamp-2 text-[11px] text-muted-foreground">
                {kb.description || "No description"}
              </p>
            </div>
          </div>
        </div>

        <nav className="mt-2 flex-1 space-y-0.5 px-2">
          {TABS.map((t) => {
            const Icon = t.icon;
            const active = t.id === tab;
            return (
              <button
                key={t.id}
                type="button"
                onClick={() => setTab(t.id)}
                className={cn(
                  "flex w-full items-center gap-2.5 rounded-md px-3 py-1.5 text-xs transition-colors",
                  active
                    ? "bg-accent font-medium text-accent-foreground"
                    : "text-muted-foreground hover:bg-accent/70 hover:text-foreground",
                )}
              >
                <Icon className="h-3.5 w-3.5" />
                {t.label}
              </button>
            );
          })}
        </nav>

        {/* Bottom stats */}
        <div className="border-t border-border p-4">
          <div className="grid grid-cols-2 gap-2 text-center">
            <Stat label="DOCUMENTS" value={kb.total_documents} />
            <Stat label="CHUNKS" value={kb.total_chunks} />
          </div>
        </div>
      </aside>

      {/* Main area */}
      <div className="flex min-w-0 flex-1 flex-col">
        {tab === "documents" && <DocumentsTab kbId={kbId} />}
        {tab === "connectors" && <ConnectorsTab kbId={kbId} />}
        {tab === "retrieval" && <RetrievalTestingTab kbId={kbId} />}
        {tab === "settings" && <KBSettingsTab kb={kb} />}
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <div className="text-sm font-semibold">{value.toLocaleString()}</div>
      <div className="text-[10px] tracking-wider text-muted-foreground">{label}</div>
    </div>
  );
}
