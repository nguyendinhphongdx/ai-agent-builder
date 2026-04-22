"use client";

import { useState } from "react";
import { Loader2, Eye, EyeOff } from "lucide-react";
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
import { Label } from "@/components/ui/label";
import {
  aiCredentialService,
  type AICredentialResponse,
} from "@/lib/api/aiCredentialService";
import { useModelCatalog, findProvider } from "@/lib/models/catalog";

interface ConnectCredentialDialogProps {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  provider: string;                                  // "openai" | "anthropic" | ...
  onCreated: (cred: AICredentialResponse) => void;   // parent handles post-create wiring
}

export function ConnectCredentialDialog({
  open,
  onOpenChange,
  provider,
  onCreated,
}: ConnectCredentialDialogProps) {
  const { data: catalog } = useModelCatalog();
  const providerInfo = findProvider(catalog?.providers, provider);
  const [name, setName] = useState("");
  const [plaintextKey, setPlaintextKey] = useState("");
  const [showKey, setShowKey] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reset = () => {
    setName("");
    setPlaintextKey("");
    setShowKey(false);
    setSaving(false);
    setError(null);
  };

  const handleSave = async () => {
    if (!plaintextKey.trim()) return;
    setSaving(true);
    setError(null);
    try {
      const created = await aiCredentialService.create({
        provider,
        name: name.trim() || `${providerInfo?.label ?? provider} credential`,
        plaintext_key: plaintextKey.trim(),
      });
      onCreated(created);
      reset();
      onOpenChange(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Không tạo được credential");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(v) => {
        if (!v) reset();
        onOpenChange(v);
      }}
    >
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Connect {providerInfo?.label ?? provider}</DialogTitle>
          <DialogDescription>
            Nhập API key để kích hoạt {providerInfo?.label ?? provider}. Key được mã hoá
            trước khi lưu và không bao giờ hiển thị lại.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3 py-1">
          <div className="space-y-1.5">
            <Label htmlFor="cred-name" className="text-xs">
              Tên credential
            </Label>
            <Input
              id="cred-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder={`VD: Prod ${providerInfo?.label ?? provider} Key`}
              className="text-sm"
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="cred-key" className="text-xs">
              API key
            </Label>
            <div className="relative">
              <Input
                id="cred-key"
                type={showKey ? "text" : "password"}
                value={plaintextKey}
                onChange={(e) => setPlaintextKey(e.target.value)}
                placeholder={provider === "openai" ? "sk-..." : "..."}
                className="pr-9 font-mono text-xs"
                onKeyDown={(e) => e.key === "Enter" && handleSave()}
                autoFocus
              />
              <button
                type="button"
                onClick={() => setShowKey((v) => !v)}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              >
                {showKey ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
              </button>
            </div>
          </div>

          {error && (
            <p className="text-xs text-destructive">{error}</p>
          )}
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              reset();
              onOpenChange(false);
            }}
          >
            Huỷ
          </Button>
          <Button
            size="sm"
            disabled={!plaintextKey.trim() || saving}
            onClick={handleSave}
          >
            {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : "Lưu credential"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
