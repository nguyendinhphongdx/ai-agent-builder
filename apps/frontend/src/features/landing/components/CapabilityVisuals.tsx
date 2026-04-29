/**
 * Compact decorative visuals shown on the right (or bottom) of each capability
 * card. Pure presentation — they don't reflect runtime data.
 */
import { Bot, Database, FileText, Globe, Lock, Sparkles, Zap } from "lucide-react";
import { cn } from "@/lib/utils";

const Pill = ({ children, className }: { children: React.ReactNode; className?: string }) => (
  <span
    className={cn(
      "inline-flex items-center gap-1.5 rounded-full border border-border bg-background px-2.5 py-1 text-[11px] font-medium text-foreground/80 shadow-sm",
      className,
    )}
  >
    {children}
  </span>
);

export function AgentsVisual() {
  return (
    <div className="relative flex h-full min-h-32 items-center justify-end gap-2 overflow-hidden">
      <div className="flex flex-col items-end gap-1.5">
        <Pill>
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" /> OpenAI · gpt-4o
        </Pill>
        <Pill>
          <span className="h-1.5 w-1.5 rounded-full bg-amber-500" /> Anthropic · sonnet
        </Pill>
        <Pill>
          <span className="h-1.5 w-1.5 rounded-full bg-violet-500" /> Ollama · llama3
        </Pill>
      </div>
      <svg width="36" height="2" className="text-border" aria-hidden>
        <line x1="0" y1="1" x2="36" y2="1" stroke="currentColor" strokeDasharray="3 3" />
      </svg>
      <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-linear-to-br from-primary to-violet-600 text-primary-foreground shadow-lg">
        <Bot className="h-5 w-5" />
      </div>
    </div>
  );
}

export function ToolsVisual() {
  const tools = [
    { Icon: Globe, label: "HTTP", tone: "text-sky-500" },
    { Icon: Database, label: "DB", tone: "text-emerald-500" },
    { Icon: Zap, label: "Code", tone: "text-amber-500" },
    { Icon: FileText, label: "Scrape", tone: "text-rose-500" },
  ];
  return (
    <div className="grid grid-cols-2 gap-2">
      {tools.map(({ Icon, label, tone }) => (
        <div
          key={label}
          className="flex items-center gap-2 rounded-lg border border-border bg-background px-2.5 py-1.5"
        >
          <Icon className={cn("h-3.5 w-3.5", tone)} />
          <span className="text-[11px] font-medium text-foreground/80">{label}</span>
        </div>
      ))}
    </div>
  );
}

export function RagVisual() {
  return (
    <div className="flex flex-wrap gap-1.5">
      {["pdf", "docx", "md", "html", "csv", "txt"].map((ext) => (
        <span
          key={ext}
          className="inline-flex items-center gap-1.5 rounded-md border border-border bg-background px-2 py-1 font-mono text-[11px] text-foreground/80"
        >
          <FileText className="h-3 w-3 text-muted-foreground" />.{ext}
        </span>
      ))}
    </div>
  );
}

export function WorkflowVisual() {
  return (
    <div className="relative flex h-full min-h-32 items-center justify-end">
      <svg viewBox="0 0 240 90" className="h-24 w-full max-w-72" aria-hidden>
        {/* edges */}
        <path
          d="M 50 25 L 120 25"
          stroke="currentColor"
          className="text-border"
          strokeWidth="1.5"
          fill="none"
          markerEnd="url(#arrow)"
        />
        <path
          d="M 120 25 Q 145 25 145 50"
          stroke="currentColor"
          className="text-border"
          strokeWidth="1.5"
          fill="none"
        />
        <path
          d="M 145 50 L 145 65 L 175 65"
          stroke="currentColor"
          className="text-border"
          strokeWidth="1.5"
          fill="none"
          markerEnd="url(#arrow)"
        />
        <path
          d="M 145 50 L 145 65 L 115 65"
          stroke="currentColor"
          className="text-border"
          strokeWidth="1.5"
          fill="none"
          markerEnd="url(#arrow)"
        />
        <defs>
          <marker id="arrow" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
            <path d="M0,0 L0,6 L6,3 z" fill="currentColor" className="text-muted-foreground" />
          </marker>
        </defs>
        {/* nodes */}
        <Node x={5} y={12} label="Input" tone="primary" />
        <Node x={75} y={12} label="LLM" tone="violet" />
        <Node x={75} y={52} label="Branch" tone="amber" />
        <Node x={155} y={52} label="Tool" tone="sky" />
        <Node x={5} y={52} label="Loop" tone="emerald" />
      </svg>
    </div>
  );
}

function Node({
  x,
  y,
  label,
  tone,
}: {
  x: number;
  y: number;
  label: string;
  tone: "primary" | "violet" | "amber" | "sky" | "emerald";
}) {
  const toneMap = {
    primary: "fill-primary/10 stroke-primary",
    violet: "fill-violet-500/10 stroke-violet-500",
    amber: "fill-amber-500/10 stroke-amber-500",
    sky: "fill-sky-500/10 stroke-sky-500",
    emerald: "fill-emerald-500/10 stroke-emerald-500",
  } as const;
  return (
    <g>
      <rect
        x={x}
        y={y}
        width="58"
        height="22"
        rx="6"
        className={cn("stroke-2", toneMap[tone])}
      />
      <text
        x={x + 29}
        y={y + 14}
        textAnchor="middle"
        className="fill-foreground/85 font-sans text-[10px] font-medium"
      >
        {label}
      </text>
    </g>
  );
}

export function MultiAgentVisual() {
  return (
    <div className="relative flex h-full min-h-32 items-center justify-end">
      <svg viewBox="0 0 240 110" className="h-28 w-full max-w-72" aria-hidden>
        <line x1="120" y1="35" x2="60" y2="80" className="text-border" stroke="currentColor" strokeWidth="1.5" strokeDasharray="3 3" />
        <line x1="120" y1="35" x2="120" y2="80" className="text-border" stroke="currentColor" strokeWidth="1.5" strokeDasharray="3 3" />
        <line x1="120" y1="35" x2="180" y2="80" className="text-border" stroke="currentColor" strokeWidth="1.5" strokeDasharray="3 3" />

        <SupNode cx={120} cy={20} label="Supervisor" tone="primary" />
        <SupNode cx={60} cy={92} label="Researcher" tone="violet" />
        <SupNode cx={120} cy={92} label="Writer" tone="amber" />
        <SupNode cx={180} cy={92} label="Reviewer" tone="emerald" />
      </svg>
    </div>
  );
}

function SupNode({
  cx,
  cy,
  label,
  tone,
}: {
  cx: number;
  cy: number;
  label: string;
  tone: "primary" | "violet" | "amber" | "emerald";
}) {
  const toneMap = {
    primary: "fill-primary/15 stroke-primary",
    violet: "fill-violet-500/15 stroke-violet-500",
    amber: "fill-amber-500/15 stroke-amber-500",
    emerald: "fill-emerald-500/15 stroke-emerald-500",
  } as const;
  return (
    <g>
      <circle cx={cx} cy={cy} r="14" className={cn("stroke-2", toneMap[tone])} />
      <text
        x={cx}
        y={cy + 4}
        textAnchor="middle"
        className="fill-foreground/85 font-sans text-[9px] font-semibold"
      >
        {label[0]}
      </text>
      <text
        x={cx}
        y={cy + 26}
        textAnchor="middle"
        className="fill-muted-foreground font-sans text-[9px]"
      >
        {label}
      </text>
    </g>
  );
}

export function SelfHostVisual() {
  return (
    <div className="overflow-hidden rounded-lg border border-border bg-foreground/4 p-3 font-mono text-[11px] text-foreground/85">
      <div className="flex items-center gap-1.5">
        <span className="text-primary">$</span>
        <span>docker compose up -d</span>
      </div>
      <div className="mt-1.5 flex items-center gap-1.5 text-emerald-500">
        <Sparkles className="h-3 w-3" />
        <span className="text-[10px] text-muted-foreground">9 services healthy in 14s</span>
      </div>
      <div className="mt-2 flex items-center gap-1 text-[10px] text-muted-foreground">
        <Lock className="h-3 w-3" />
        <span>encrypted · MIT · no telemetry</span>
      </div>
    </div>
  );
}

export function getVisualFor(id: string) {
  switch (id) {
    case "agents":
      return <AgentsVisual />;
    case "tools":
      return <ToolsVisual />;
    case "rag":
      return <RagVisual />;
    case "workflows":
      return <WorkflowVisual />;
    case "multi":
      return <MultiAgentVisual />;
    case "selfhost":
      return <SelfHostVisual />;
    default:
      return null;
  }
}
