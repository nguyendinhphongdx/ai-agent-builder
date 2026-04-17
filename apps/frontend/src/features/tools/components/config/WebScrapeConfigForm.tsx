"use client";

import { Globe } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";

interface WebScrapeConfig {
  url_template: string;
  max_length: number;
  css_selector?: string;
  extract_type: "text" | "html" | "links";
  wait_for_js: boolean;
}

function parseConfig(raw: Record<string, unknown>): WebScrapeConfig {
  return {
    url_template: (raw.url_template as string) ?? "",
    max_length: typeof raw.max_length === "number" ? raw.max_length : 5000,
    css_selector: (raw.css_selector as string) ?? "",
    extract_type: (raw.extract_type as WebScrapeConfig["extract_type"]) ?? "text",
    wait_for_js: Boolean(raw.wait_for_js),
  };
}

interface WebScrapeConfigFormProps {
  value: Record<string, unknown>;
  onChange: (value: Record<string, unknown>) => void;
}

export function WebScrapeConfigForm({ value, onChange }: WebScrapeConfigFormProps) {
  const cfg = parseConfig(value);

  const update = (patch: Partial<WebScrapeConfig>) => {
    onChange({ ...cfg, ...patch });
  };

  return (
    <div className="space-y-5">
      {/* URL Template */}
      <div className="space-y-1.5">
        <Label className="text-xs text-muted-foreground">URL Template</Label>
        <div className="relative">
          <Globe className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
          <Input
            className="h-9 pl-8 font-mono text-xs"
            placeholder="https://example.com/{path}"
            value={cfg.url_template}
            onChange={(e) => update({ url_template: e.target.value })}
          />
        </div>
        <p className="text-[11px] text-muted-foreground">
          Use <code className="rounded bg-muted px-1">{"{variable}"}</code> for dynamic URL parts.
        </p>
      </div>

      {/* CSS Selector */}
      <div className="space-y-1.5">
        <Label className="text-xs text-muted-foreground">CSS Selector (optional)</Label>
        <Input
          className="h-8 font-mono text-xs"
          placeholder=".article-content, #main-body, h1"
          value={cfg.css_selector ?? ""}
          onChange={(e) => update({ css_selector: e.target.value })}
        />
        <p className="text-[11px] text-muted-foreground">
          Leave blank to scrape the full body. Use any valid CSS selector.
        </p>
      </div>

      {/* Extract mode */}
      <div className="space-y-1.5">
        <Label className="text-xs text-muted-foreground">Extract mode</Label>
        <Select
          value={cfg.extract_type}
          onValueChange={(v) => update({ extract_type: v as WebScrapeConfig["extract_type"] })}
        >
          <SelectTrigger className="h-8 w-48 text-xs">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="text" className="text-xs">
              Readable text (cleaned)
            </SelectItem>
            <SelectItem value="html" className="text-xs">
              Raw HTML
            </SelectItem>
            <SelectItem value="links" className="text-xs">
              All links
            </SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Max length */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <Label className="text-xs text-muted-foreground">Max content length</Label>
          <span className="font-mono text-xs font-medium">{cfg.max_length.toLocaleString()} chars</span>
        </div>
        <Slider
          min={500}
          max={50000}
          step={500}
          value={[cfg.max_length]}
          onValueChange={([v]) => update({ max_length: v })}
        />
        <p className="text-[11px] text-muted-foreground">
          Limit response to avoid excessive token usage. Recommended: 5,000–10,000.
        </p>
      </div>

      {/* JS rendering */}
      <div className="flex items-center gap-3 rounded-lg border border-border/70 p-3">
        <Switch
          checked={cfg.wait_for_js}
          onCheckedChange={(v) => update({ wait_for_js: v })}
        />
        <div className="space-y-0.5">
          <p className="text-xs font-medium">Wait for JavaScript</p>
          <p className="text-[11px] text-muted-foreground">
            Enable for SPAs and pages with dynamic content. Requires a headless browser.
          </p>
        </div>
      </div>
    </div>
  );
}
