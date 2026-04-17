import Link from "next/link";
import {
  Bot,
  Wrench,
  BookOpen,
  GitBranch,
  Users,
  ArrowRight,
  Sparkles,
  Zap,
  Check,
  Globe,
  Cpu,
  Lock,
  MessageSquare,
  Layers,
  ChevronRight,
} from "lucide-react";
import { cn } from "@/lib/utils";

const features = [
  {
    icon: Wrench,
    title: "Custom Tools",
    description:
      "Define API calls, code execution, database queries, and web scraping. Your agents call any service you connect.",
    color: "bg-amber-50 text-amber-600 border-amber-200",
    iconBg: "bg-amber-100",
  },
  {
    icon: BookOpen,
    title: "Knowledge Base (RAG)",
    description:
      "Upload PDFs, docs, and text files. Auto-chunk, embed with OpenAI, and retrieve via pgvector similarity search.",
    color: "bg-emerald-50 text-emerald-600 border-emerald-200",
    iconBg: "bg-emerald-100",
  },
  {
    icon: GitBranch,
    title: "Visual Workflow Builder",
    description:
      "Drag-and-drop editor to chain LLM calls, tools, conditions, human-in-the-loop, and subgraph nodes.",
    color: "bg-violet-50 text-violet-600 border-violet-200",
    iconBg: "bg-violet-100",
  },
  {
    icon: Users,
    title: "Multi-Agent Collaboration",
    description:
      "Supervisor and peer patterns. Multiple specialized agents work together on complex tasks.",
    color: "bg-sky-50 text-sky-600 border-sky-200",
    iconBg: "bg-sky-100",
  },
  {
    icon: MessageSquare,
    title: "Streaming Chat",
    description:
      "Real-time WebSocket streaming with tool call indicators, markdown rendering, and conversation history.",
    color: "bg-rose-50 text-rose-600 border-rose-200",
    iconBg: "bg-rose-100",
  },
  {
    icon: Lock,
    title: "Enterprise Security",
    description:
      "JWT auth with httpOnly cookies, encrypted API keys, sandboxed code execution, read-only DB queries.",
    color: "bg-slate-50 text-slate-600 border-slate-200",
    iconBg: "bg-slate-100",
  },
];

const integrations = [
  { name: "OpenAI", sub: "GPT-4o, Embeddings" },
  { name: "Anthropic", sub: "Claude Sonnet, Haiku" },
  { name: "LangChain", sub: "Tools, Splitters" },
  { name: "LangGraph", sub: "Workflows, Agents" },
  { name: "PostgreSQL", sub: "pgvector, Async" },
  { name: "Next.js", sub: "App Router, RSC" },
];

const steps = [
  {
    step: "01",
    title: "Create an Agent",
    description: "Name it, write instructions, pick a model. Choose from OpenAI or Anthropic.",
    icon: Bot,
  },
  {
    step: "02",
    title: "Add Knowledge & Tools",
    description: "Upload documents for RAG. Attach API tools, code executors, or web scrapers.",
    icon: Layers,
  },
  {
    step: "03",
    title: "Build Workflows",
    description: "Design multi-step flows visually. Add conditions, loops, and human checkpoints.",
    icon: GitBranch,
  },
  {
    step: "04",
    title: "Deploy & Chat",
    description: "Test in the live preview. Deploy to production with streaming responses.",
    icon: Zap,
  },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-white text-slate-900 selection:bg-blue-100">
      {/* Navigation */}
      <nav className="sticky top-0 z-50 border-b border-slate-200/80 bg-white/80 backdrop-blur-lg">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-3 lg:px-8">
          <Link href="/" className="flex items-center gap-2.5 group">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600 transition-transform group-hover:scale-105">
              <Bot className="h-4 w-4 text-white" />
            </div>
            <span className="text-base font-bold tracking-tight">AgentForge</span>
          </Link>
          <div className="hidden md:flex items-center gap-8 text-sm text-slate-500">
            <a href="#features" className="hover:text-slate-900 transition-colors">Features</a>
            <a href="#how-it-works" className="hover:text-slate-900 transition-colors">How it works</a>
            <a href="#integrations" className="hover:text-slate-900 transition-colors">Integrations</a>
          </div>
          <div className="flex items-center gap-3">
            <Link
              href="/login"
              className="text-sm font-medium text-slate-600 hover:text-slate-900 transition-colors px-3 py-2"
            >
              Sign in
            </Link>
            <Link
              href="/register"
              className="text-sm font-semibold bg-blue-600 text-white px-4 py-2 rounded-lg transition-all hover:bg-blue-700 active:scale-[0.98] shadow-sm shadow-blue-600/25"
            >
              Get Started Free
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative overflow-hidden">
        {/* Background decoration */}
        <div className="pointer-events-none absolute inset-0">
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[1000px] h-[600px] bg-gradient-to-b from-blue-50 via-indigo-50/50 to-transparent rounded-full blur-3xl opacity-60" />
          <div className="absolute top-20 right-0 w-72 h-72 bg-gradient-to-br from-amber-100/40 to-transparent rounded-full blur-3xl" />
          <div className="absolute top-40 left-0 w-72 h-72 bg-gradient-to-br from-emerald-100/40 to-transparent rounded-full blur-3xl" />
        </div>

        {/* Grid pattern */}
        <div
          className="pointer-events-none absolute inset-0 opacity-[0.03]"
          style={{
            backgroundImage: "radial-gradient(circle, #000 1px, transparent 1px)",
            backgroundSize: "24px 24px",
          }}
        />

        <div className="relative mx-auto max-w-7xl px-6 pt-20 pb-24 md:pt-28 md:pb-32 lg:px-8">
          <div className="mx-auto max-w-3xl text-center">
            {/* Badge */}
            <div className="animate-fade-up mb-6 inline-flex items-center gap-2 rounded-full border border-blue-200 bg-blue-50 px-4 py-1.5 text-xs font-medium text-blue-700">
              <Sparkles className="h-3.5 w-3.5" />
              Open Source AI Agent Platform
              <ChevronRight className="h-3 w-3" />
            </div>

            {/* Headline */}
            <h1 className="animate-fade-up delay-100 text-4xl font-extrabold tracking-tight leading-[1.1] sm:text-5xl md:text-6xl lg:text-[4.25rem]">
              The platform to{" "}
              <span className="bg-gradient-to-r from-blue-600 via-indigo-600 to-violet-600 bg-clip-text text-transparent">
                build, deploy & scale
              </span>{" "}
              AI agents
            </h1>

            {/* Subtitle */}
            <p className="animate-fade-up delay-200 mt-6 text-lg text-slate-500 leading-relaxed md:text-xl max-w-2xl mx-auto">
              Create intelligent agents with custom tools, knowledge bases,
              visual workflows, and multi-agent orchestration.
              Powered by LangGraph & LangChain.
            </p>

            {/* CTA buttons */}
            <div className="animate-fade-up delay-300 mt-10 flex flex-col gap-3 sm:flex-row sm:justify-center sm:gap-4">
              <Link
                href="/register"
                className="inline-flex items-center justify-center gap-2 rounded-xl bg-blue-600 px-7 py-3 text-sm font-semibold text-white shadow-lg shadow-blue-600/25 transition-all hover:bg-blue-700 hover:shadow-blue-600/35 hover:shadow-xl active:scale-[0.98]"
              >
                Start Building Free
                <ArrowRight className="h-4 w-4" />
              </Link>
              <Link
                href="#how-it-works"
                className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-300 bg-white px-7 py-3 text-sm font-semibold text-slate-700 shadow-sm transition-all hover:bg-slate-50 hover:border-slate-400"
              >
                See How It Works
              </Link>
            </div>

            {/* Stats */}
            <div className="animate-fade-up delay-400 mt-14 grid grid-cols-4 gap-4 mx-auto max-w-lg">
              {[
                ["5+", "LLM Models"],
                ["6", "File Types"],
                ["8", "Node Types"],
                ["100%", "Open Source"],
              ].map(([value, label]) => (
                <div key={label} className="text-center">
                  <div className="text-2xl font-bold text-slate-900">{value}</div>
                  <div className="mt-0.5 text-[11px] text-slate-400 font-medium">{label}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Hero graphic - Mock UI */}
          <div className="animate-fade-up delay-500 mt-16 mx-auto max-w-5xl">
            <div className="rounded-2xl border border-slate-200 bg-white shadow-2xl shadow-slate-200/50 overflow-hidden">
              {/* Window chrome */}
              <div className="flex items-center gap-2 border-b border-slate-100 px-4 py-3">
                <div className="flex gap-1.5">
                  <div className="h-3 w-3 rounded-full bg-red-400" />
                  <div className="h-3 w-3 rounded-full bg-amber-400" />
                  <div className="h-3 w-3 rounded-full bg-emerald-400" />
                </div>
                <div className="flex-1 text-center">
                  <span className="text-xs text-slate-400 bg-slate-50 px-3 py-1 rounded-md">agentforge.app/agents/new</span>
                </div>
              </div>
              {/* Simulated UI */}
              <div className="flex h-[340px] md:h-[400px]">
                {/* Left panel mock */}
                <div className="w-48 border-r border-slate-100 bg-slate-50/50 p-4 hidden sm:block">
                  <div className="space-y-2">
                    {["Libraries", "Tools", "Workflows"].map((item, i) => (
                      <div key={item} className={cn("flex items-center gap-2 rounded-lg px-3 py-1.5 text-xs", i === 0 ? "bg-blue-50 text-blue-700 font-medium" : "text-slate-400")}>
                        <div className={cn("h-1.5 w-1.5 rounded-full", i === 0 ? "bg-blue-500" : "bg-slate-300")} />
                        {item}
                      </div>
                    ))}
                  </div>
                </div>
                {/* Config panel mock */}
                <div className="flex-1 border-r border-slate-100 p-6 space-y-4">
                  <div>
                    <div className="text-[10px] font-medium text-slate-400 mb-1.5">AGENT NAME</div>
                    <div className="h-8 rounded-lg border border-slate-200 bg-white px-3 flex items-center text-xs text-slate-700">Customer Support Bot</div>
                  </div>
                  <div>
                    <div className="text-[10px] font-medium text-slate-400 mb-1.5">INSTRUCTIONS</div>
                    <div className="h-20 rounded-lg border border-slate-200 bg-white p-3 text-[11px] text-slate-500 leading-relaxed">You are a helpful customer support agent. Use the knowledge base to answer questions about our products...</div>
                  </div>
                  <div className="flex gap-2">
                    <div className="flex-1">
                      <div className="text-[10px] font-medium text-slate-400 mb-1.5">PROVIDER</div>
                      <div className="h-8 rounded-lg border border-slate-200 bg-white px-3 flex items-center text-xs text-slate-600">OpenAI</div>
                    </div>
                    <div className="flex-1">
                      <div className="text-[10px] font-medium text-slate-400 mb-1.5">MODEL</div>
                      <div className="h-8 rounded-lg border border-slate-200 bg-white px-3 flex items-center text-xs text-slate-600">GPT-4o</div>
                    </div>
                  </div>
                  <div>
                    <div className="text-[10px] font-medium text-slate-400 mb-1.5">TOOLS</div>
                    <div className="flex gap-2">
                      <span className="inline-flex items-center gap-1 rounded-md bg-amber-50 border border-amber-200 px-2 py-1 text-[10px] font-medium text-amber-700"><Globe className="h-2.5 w-2.5" />Web Search</span>
                      <span className="inline-flex items-center gap-1 rounded-md bg-emerald-50 border border-emerald-200 px-2 py-1 text-[10px] font-medium text-emerald-700"><BookOpen className="h-2.5 w-2.5" />Knowledge</span>
                    </div>
                  </div>
                </div>
                {/* Chat preview mock */}
                <div className="w-[280px] md:w-[320px] bg-slate-50/30 p-4 flex flex-col hidden md:flex">
                  <div className="text-[10px] font-medium text-slate-400 mb-3">PREVIEW</div>
                  <div className="flex-1 space-y-3">
                    <div className="flex gap-2">
                      <div className="h-5 w-5 rounded-md bg-slate-200 shrink-0 flex items-center justify-center"><span className="text-[8px]">U</span></div>
                      <div className="rounded-lg bg-blue-50 border border-blue-100 px-3 py-1.5 text-[11px] text-slate-700">How do I reset my password?</div>
                    </div>
                    <div className="flex gap-2">
                      <div className="h-5 w-5 rounded-md bg-blue-100 shrink-0 flex items-center justify-center"><Bot className="h-2.5 w-2.5 text-blue-600" /></div>
                      <div className="rounded-lg bg-white border border-slate-100 px-3 py-1.5 text-[11px] text-slate-600 leading-relaxed">
                        To reset your password, go to <strong>Settings &gt; Security</strong> and click &quot;Reset Password&quot;. You&apos;ll receive a confirmation email within 2 minutes.
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <div className="h-5 w-5 rounded-md bg-blue-100 shrink-0 flex items-center justify-center"><Bot className="h-2.5 w-2.5 text-blue-600" /></div>
                      <div className="flex items-center gap-1 px-3 py-2">
                        <span className="inline-flex items-center gap-1 text-[9px] text-emerald-600 font-medium"><BookOpen className="h-2.5 w-2.5" />Searched Knowledge Base</span>
                      </div>
                    </div>
                  </div>
                  <div className="mt-2 flex gap-2">
                    <div className="flex-1 h-8 rounded-lg border border-slate-200 bg-white px-3 flex items-center text-[11px] text-slate-300">Send a message...</div>
                    <div className="h-8 w-8 rounded-lg bg-blue-600 flex items-center justify-center"><ArrowRight className="h-3 w-3 text-white" /></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="border-t border-slate-100 bg-slate-50/50">
        <div className="mx-auto max-w-7xl px-6 py-24 md:py-32 lg:px-8">
          <div className="mx-auto max-w-2xl text-center mb-16">
            <p className="mb-3 text-sm font-semibold text-blue-600">Capabilities</p>
            <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
              Everything you need for
              <br />production-grade AI agents
            </h2>
            <p className="mt-4 text-base text-slate-500 leading-relaxed">
              From simple chatbots to complex multi-agent systems — AgentForge provides the building blocks.
            </p>
          </div>

          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {features.map((feature, i) => (
              <div
                key={feature.title}
                className={cn(
                  "animate-fade-up group relative rounded-2xl border bg-white p-6 shadow-sm transition-all duration-300 hover:shadow-md hover:-translate-y-0.5",
                  feature.color.split(" ")[2], // border color
                  i === 0 && "delay-100",
                  i === 1 && "delay-200",
                  i === 2 && "delay-300",
                  i === 3 && "delay-400",
                  i === 4 && "delay-500",
                  i === 5 && "delay-600"
                )}
              >
                <div className={cn("mb-4 inline-flex h-11 w-11 items-center justify-center rounded-xl", feature.iconBg)}>
                  <feature.icon className={cn("h-5 w-5", feature.color.split(" ")[1])} />
                </div>
                <h3 className="mb-2 text-base font-bold text-slate-900">
                  {feature.title}
                </h3>
                <p className="text-sm leading-relaxed text-slate-500">
                  {feature.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section id="how-it-works" className="border-t border-slate-100">
        <div className="mx-auto max-w-7xl px-6 py-24 md:py-32 lg:px-8">
          <div className="mx-auto max-w-2xl text-center mb-16">
            <p className="mb-3 text-sm font-semibold text-blue-600">How it works</p>
            <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
              From zero to deployed in 4 steps
            </h2>
          </div>

          <div className="grid gap-8 md:grid-cols-2 lg:grid-cols-4">
            {steps.map((s, i) => (
              <div key={s.step} className={cn("animate-fade-up relative", i === 0 && "delay-100", i === 1 && "delay-200", i === 2 && "delay-300", i === 3 && "delay-400")}>
                {/* Connector line */}
                {i < steps.length - 1 && (
                  <div className="hidden lg:block absolute top-8 left-[calc(100%+1rem)] w-[calc(100%-2rem)] border-t-2 border-dashed border-slate-200" />
                )}
                <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-blue-50 border border-blue-100 mb-5">
                  <s.icon className="h-7 w-7 text-blue-600" />
                </div>
                <span className="text-xs font-bold text-blue-600 uppercase tracking-wider">{s.step}</span>
                <h3 className="mt-2 text-lg font-bold text-slate-900">{s.title}</h3>
                <p className="mt-2 text-sm text-slate-500 leading-relaxed">{s.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Integrations */}
      <section id="integrations" className="border-t border-slate-100 bg-slate-50/50">
        <div className="mx-auto max-w-7xl px-6 py-24 md:py-32 lg:px-8">
          <div className="mx-auto max-w-2xl text-center mb-16">
            <p className="mb-3 text-sm font-semibold text-blue-600">Tech Stack</p>
            <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
              Built on proven technology
            </h2>
            <p className="mt-4 text-base text-slate-500">
              Enterprise-grade stack with the best tools in the AI ecosystem.
            </p>
          </div>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 max-w-3xl mx-auto">
            {integrations.map((int) => (
              <div
                key={int.name}
                className="flex items-center gap-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm hover:shadow-md transition-shadow"
              >
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-slate-100">
                  <Cpu className="h-5 w-5 text-slate-600" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-slate-900">{int.name}</p>
                  <p className="text-xs text-slate-400">{int.sub}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Bottom CTA */}
      <section className="border-t border-slate-100">
        <div className="mx-auto max-w-7xl px-6 py-24 md:py-32 lg:px-8">
          <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-blue-600 via-indigo-600 to-violet-600 p-12 text-center md:p-20 shadow-xl">
            {/* Decorations */}
            <div className="pointer-events-none absolute top-0 left-0 w-64 h-64 bg-white/10 rounded-full blur-3xl -translate-x-1/2 -translate-y-1/2" />
            <div className="pointer-events-none absolute bottom-0 right-0 w-80 h-80 bg-white/5 rounded-full blur-3xl translate-x-1/3 translate-y-1/3" />

            <div className="relative">
              <div className="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-2xl bg-white/20 backdrop-blur ring-1 ring-white/25">
                <Bot className="h-7 w-7 text-white" />
              </div>
              <h2 className="text-3xl font-bold text-white sm:text-4xl">
                Ready to build your AI agents?
              </h2>
              <p className="mx-auto mt-4 max-w-lg text-base text-white/70 leading-relaxed">
                Join developers building the next generation of intelligent applications.
                Free to start, open source forever.
              </p>
              <div className="mt-8 flex flex-col sm:flex-row gap-3 justify-center">
                <Link
                  href="/register"
                  className="inline-flex items-center justify-center gap-2 rounded-xl bg-white px-7 py-3 text-sm font-semibold text-blue-700 shadow-lg transition-all hover:shadow-xl hover:bg-blue-50 active:scale-[0.98]"
                >
                  Get Started Free
                  <ArrowRight className="h-4 w-4" />
                </Link>
                <Link
                  href="/login"
                  className="inline-flex items-center justify-center gap-2 rounded-xl border border-white/30 bg-white/10 px-7 py-3 text-sm font-semibold text-white backdrop-blur transition-all hover:bg-white/20"
                >
                  Sign In
                </Link>
              </div>
              <div className="mt-8 flex justify-center gap-6 text-sm text-white/60">
                {["No credit card required", "Open source", "Self-hostable"].map((t) => (
                  <span key={t} className="flex items-center gap-1.5">
                    <Check className="h-3.5 w-3.5 text-emerald-300" />
                    {t}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-slate-200 bg-white">
        <div className="mx-auto max-w-7xl px-6 py-8 lg:px-8">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-blue-600">
                <Bot className="h-3.5 w-3.5 text-white" />
              </div>
              <span className="text-sm font-bold">AgentForge</span>
            </div>
            <div className="flex items-center gap-6 text-sm text-slate-400">
              <a href="#features" className="hover:text-slate-600 transition-colors">Features</a>
              <a href="#how-it-works" className="hover:text-slate-600 transition-colors">How it works</a>
              <a href="#integrations" className="hover:text-slate-600 transition-colors">Integrations</a>
            </div>
            <p className="text-xs text-slate-400">
              Open source AI agent builder platform
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
