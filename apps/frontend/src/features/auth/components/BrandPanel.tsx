"use client";

import { Bot, Workflow, Database, Sparkles } from "lucide-react";

function AgentIllustration() {
  return (
    <div className="relative w-full max-w-[420px] mx-auto" style={{ aspectRatio: "420/480" }}>
      {/* Ambient glow */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-48 h-48 rounded-full bg-blue-400/8 blur-[60px]" />

      <svg
        viewBox="0 0 420 480"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="w-full h-full relative z-10"
      >
        <defs>
          <marker id="arr" viewBox="0 0 8 6" refX="7" refY="3" markerWidth="7" markerHeight="5" orient="auto-start-reverse">
            <path d="M0,0.8 L6,3 L0,5.2" fill="#94a3b8" />
          </marker>
        </defs>

        {/* ═══ TOP: Agent hub with resource nodes ═══ */}

        {/* Connection lines to agent */}
        <g className="animate-fade-in delay-300" opacity="0.4">
          <path d="M104 78 C145 88, 162 112, 184 128" stroke="#cbd5e1" strokeWidth="1.2" strokeDasharray="4 3">
            <animate attributeName="stroke-dashoffset" from="0" to="-14" dur="2s" repeatCount="indefinite" />
          </path>
          <path d="M316 78 C275 88, 258 112, 236 128" stroke="#cbd5e1" strokeWidth="1.2" strokeDasharray="4 3">
            <animate attributeName="stroke-dashoffset" from="0" to="-14" dur="2.4s" repeatCount="indefinite" />
          </path>
          <path d="M82 166 C115 160, 148 150, 178 143" stroke="#cbd5e1" strokeWidth="1.2" strokeDasharray="4 3">
            <animate attributeName="stroke-dashoffset" from="0" to="-14" dur="2.2s" repeatCount="indefinite" />
          </path>
          <path d="M338 166 C305 160, 272 150, 242 143" stroke="#cbd5e1" strokeWidth="1.2" strokeDasharray="4 3">
            <animate attributeName="stroke-dashoffset" from="0" to="-14" dur="1.8s" repeatCount="indefinite" />
          </path>
        </g>

        {/* Resource nodes */}
        <g className="animate-fade-in delay-200">
          {/* LLM */}
          <g className="animate-float">
            <rect x="56" y="44" width="68" height="46" rx="12" fill="white" stroke="#e2e8f0" strokeWidth="1.2" />
            <rect x="66" y="54" width="8" height="8" rx="2" fill="#818cf8" opacity="0.8" />
            <text x="80" y="62" className="text-[10px] font-semibold" fill="#475569">LLM</text>
            <rect x="66" y="72" width="42" height="3.5" rx="2" fill="#e2e8f0" />
            <rect x="66" y="78" width="28" height="3" rx="2" fill="#f1f5f9" />
          </g>

          {/* Tool */}
          <g className="animate-float delay-200">
            <rect x="296" y="44" width="68" height="46" rx="12" fill="white" stroke="#e2e8f0" strokeWidth="1.2" />
            <rect x="306" y="54" width="8" height="8" rx="2" fill="#f472b6" opacity="0.8" />
            <text x="320" y="62" className="text-[10px] font-semibold" fill="#475569">Tool</text>
            <rect x="306" y="72" width="42" height="3.5" rx="2" fill="#e2e8f0" />
            <rect x="306" y="78" width="28" height="3" rx="2" fill="#f1f5f9" />
          </g>

          {/* KB */}
          <g className="animate-float delay-400">
            <rect x="14" y="140" width="68" height="46" rx="12" fill="white" stroke="#e2e8f0" strokeWidth="1.2" />
            <rect x="24" y="150" width="8" height="8" rx="2" fill="#a78bfa" opacity="0.8" />
            <text x="38" y="158" className="text-[10px] font-semibold" fill="#475569">KB</text>
            <rect x="24" y="168" width="42" height="3.5" rx="2" fill="#e2e8f0" />
            <rect x="24" y="174" width="28" height="3" rx="2" fill="#f1f5f9" />
          </g>

          {/* API */}
          <g className="animate-float delay-600">
            <rect x="338" y="140" width="68" height="46" rx="12" fill="white" stroke="#e2e8f0" strokeWidth="1.2" />
            <rect x="348" y="150" width="8" height="8" rx="2" fill="#34d399" opacity="0.8" />
            <text x="362" y="158" className="text-[10px] font-semibold" fill="#475569">API</text>
            <rect x="348" y="168" width="42" height="3.5" rx="2" fill="#e2e8f0" />
            <rect x="348" y="174" width="28" height="3" rx="2" fill="#f1f5f9" />
          </g>
        </g>

        {/* Central AI Agent */}
        <g className="animate-fade-up">
          {/* Pulse ring */}
          <circle cx="210" cy="148" r="44" fill="none" stroke="#818cf8" strokeWidth="0.8" opacity="0.12">
            <animate attributeName="r" values="44;50;44" dur="3.5s" repeatCount="indefinite" />
            <animate attributeName="opacity" values="0.12;0.25;0.12" dur="3.5s" repeatCount="indefinite" />
          </circle>
          <circle cx="210" cy="148" r="38" fill="#eef2ff" opacity="0.5" />

          {/* Body */}
          <rect x="184" y="122" width="52" height="52" rx="15" fill="#6366f1" />
          <rect x="184" y="122" width="52" height="52" rx="15" fill="none" stroke="white" strokeWidth="0.5" opacity="0.25" />

          {/* Face */}
          <circle cx="198" cy="144" r="3.5" fill="white" />
          <circle cx="222" cy="144" r="3.5" fill="white" />
          <path d="M198 156 Q210 163, 222 156" stroke="white" strokeWidth="2.5" strokeLinecap="round" fill="none" />

          {/* Antenna */}
          <line x1="210" y1="122" x2="210" y2="110" stroke="#6366f1" strokeWidth="2" strokeLinecap="round" />
          <circle cx="210" cy="106" r="4" fill="#818cf8">
            <animate attributeName="opacity" values="0.5;1;0.5" dur="2s" repeatCount="indefinite" />
          </circle>
        </g>

        {/* ═══ BOTTOM: Workflow Pipeline ═══ */}

        {/* Connector agent -> workflow */}
        <g className="animate-fade-in delay-400">
          <line x1="210" y1="178" x2="210" y2="225" stroke="#818cf8" strokeWidth="1" opacity="0.25" strokeDasharray="3 3">
            <animate attributeName="stroke-dashoffset" from="0" to="-12" dur="1.5s" repeatCount="indefinite" />
          </line>
          <polygon points="206,222 210,230 214,222" fill="#818cf8" opacity="0.3" />
        </g>

        {/* Workflow edges */}
        <g className="animate-fade-in delay-500">
          <line x1="118" y1="264" x2="152" y2="264" stroke="#94a3b8" strokeWidth="1.2" markerEnd="url(#arr)" />
          <line x1="218" y1="264" x2="248" y2="264" stroke="#94a3b8" strokeWidth="1.2" markerEnd="url(#arr)" />
          <path d="M300 252 C314 242, 326 236, 346 236" stroke="#94a3b8" strokeWidth="1.2" markerEnd="url(#arr)" />
          <path d="M300 276 C314 286, 326 292, 346 292" stroke="#94a3b8" strokeWidth="1.2" markerEnd="url(#arr)" />
        </g>

        {/* Workflow nodes */}
        <g className="animate-fade-in delay-500">
          {/* Input (green circle) */}
          <circle cx="98" cy="264" r="20" fill="#f0fdf4" stroke="#86efac" strokeWidth="1.5" />
          <rect x="90" y="256" width="6" height="6" rx="1.5" fill="#22c55e" opacity="0.7" />
          <text x="98" y="274" textAnchor="middle" className="text-[8px] font-semibold" fill="#16a34a">Input</text>

          {/* Agent (blue rect) */}
          <rect x="155" y="240" width="63" height="48" rx="12" fill="#eef2ff" stroke="#a5b4fc" strokeWidth="1.5" />
          <rect x="170" y="250" width="12" height="12" rx="3.5" fill="#6366f1" />
          <circle cx="174" cy="255" r="1.5" fill="white" />
          <circle cx="178" cy="255" r="1.5" fill="white" />
          <text x="186" y="276" textAnchor="middle" className="text-[8px] font-semibold" fill="#4f46e5">Agent</text>

          {/* Condition (amber diamond) */}
          <polygon points="275,238 300,264 275,290 250,264" fill="#fefce8" stroke="#fcd34d" strokeWidth="1.5" />
          <text x="275" y="262" textAnchor="middle" className="text-[10px] font-bold" fill="#a16207">?</text>
          <text x="275" y="274" textAnchor="middle" className="text-[6.5px] font-medium" fill="#ca8a04">check</text>

          {/* Yes / No labels */}
          <rect x="308" y="232" width="24" height="13" rx="4" fill="#dcfce7" stroke="#86efac" strokeWidth="0.8" />
          <text x="320" y="242" textAnchor="middle" className="text-[7px] font-bold" fill="#16a34a">Yes</text>

          <rect x="308" y="286" width="22" height="13" rx="4" fill="#fef2f2" stroke="#fca5a5" strokeWidth="0.8" />
          <text x="319" y="296" textAnchor="middle" className="text-[7px] font-bold" fill="#dc2626">No</text>

          {/* Tool (pink rect, Yes branch) */}
          <rect x="348" y="220" width="54" height="32" rx="9" fill="#fdf2f8" stroke="#f9a8d4" strokeWidth="1.5" />
          <rect x="358" y="229" width="6" height="6" rx="1.5" fill="#ec4899" opacity="0.7" />
          <text x="375" y="246" textAnchor="middle" className="text-[8px] font-semibold" fill="#be185d">Tool</text>

          {/* End (purple circle, No branch) */}
          <circle cx="374" cy="292" r="17" fill="#f5f3ff" stroke="#c4b5fd" strokeWidth="1.5" />
          <text x="374" y="296" textAnchor="middle" className="text-[8px] font-semibold" fill="#7c3aed">End</text>
        </g>

        {/* Animated data particles */}
        <g>
          <circle r="3" fill="#6366f1" opacity="0.5">
            <animateMotion dur="3.5s" repeatCount="indefinite" path="M98,264 L155,264 L218,264 L275,264 L300,252 C314,242 326,236 374,236" />
            <animate attributeName="opacity" values="0.3;0.7;0.3" dur="3.5s" repeatCount="indefinite" />
          </circle>
          <circle r="2.5" fill="#8b5cf6" opacity="0.4">
            <animateMotion dur="4.5s" repeatCount="indefinite" begin="1.5s" path="M98,264 L155,264 L218,264 L275,264 L300,276 C314,286 326,292 374,292" />
            <animate attributeName="opacity" values="0.2;0.6;0.2" dur="4.5s" repeatCount="indefinite" />
          </circle>
        </g>

        {/* Section label */}
        <g className="animate-fade-in delay-700">
          <line x1="70" y1="332" x2="350" y2="332" stroke="#e2e8f0" strokeWidth="0.8" />
          <text x="210" y="354" textAnchor="middle" fill="#94a3b8" fontSize="8.5" fontWeight="600" letterSpacing="0.18em">VISUAL WORKFLOW BUILDER</text>
        </g>

        {/* Ambient particles */}
        <g opacity="0.2">
          <circle cx="155" cy="100" r="1.5" fill="#818cf8" className="animate-float delay-100" />
          <circle cx="270" cy="195" r="1" fill="#f472b6" className="animate-float delay-300" />
          <circle cx="40" cy="230" r="1.5" fill="#a78bfa" className="animate-float delay-500" />
          <circle cx="380" cy="115" r="1" fill="#34d399" className="animate-float delay-700" />
        </g>
      </svg>
    </div>
  );
}

const features = [
  { icon: Workflow, label: "Visual Workflows", color: "#eab308" },
  { icon: Database, label: "Knowledge Base", color: "#8b5cf6" },
  { icon: Sparkles, label: "Multi-Agent", color: "#6366f1" },
];

export function BrandPanel() {
  return (
    <div className="hidden lg:flex flex-col justify-between h-full bg-muted/30 border-r border-border p-10 relative overflow-hidden">
      {/* Dot grid */}
      <div
        className="absolute inset-0 opacity-[0.02]"
        style={{
          backgroundImage: `radial-gradient(circle at 1px 1px, currentColor 0.8px, transparent 0)`,
          backgroundSize: "28px 28px",
        }}
      />

      {/* Top: Logo + tagline */}
      <div className="relative z-10 animate-fade-up">
        <div className="flex items-center gap-3 mb-4">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl text-white" style={{ background: "#6366f1" }}>
            <Bot className="h-5 w-5" />
          </div>
          <span className="text-xl font-semibold tracking-tight">AgentForge</span>
        </div>
        <p className="text-muted-foreground text-[15px] leading-relaxed max-w-[280px]">
          Build, deploy, and orchestrate AI agents with tools, knowledge, and visual workflows.
        </p>
      </div>

      {/* Center: Illustration */}
      <div className="relative z-10 flex-1 flex items-center justify-center py-4">
        <AgentIllustration />
      </div>

      {/* Bottom: Feature highlights */}
      <div className="relative z-10 flex gap-6 animate-fade-up delay-400">
        {features.map(({ icon: Icon, label, color }) => (
          <div key={label} className="flex items-center gap-2 text-muted-foreground">
            <Icon className="h-4 w-4" style={{ color }} />
            <span className="text-xs font-medium">{label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
