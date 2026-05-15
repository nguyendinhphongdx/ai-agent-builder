import Link from "next/link";
import { Bot } from "lucide-react";
import { SITE } from "../data/content";
import { GithubIcon } from "./icons";

const COLUMNS = [
  {
    title: "Product",
    links: [
      { label: "Capabilities", href: "#capabilities" },
      { label: "Integrate", href: "#integrate" },
      { label: "Compare", href: "#compare" },
      { label: "How it works", href: "#how" },
    ],
  },
  {
    title: "Resources",
    links: [
      { label: "Documentation", href: "/docs" },
      { label: "GitHub", href: SITE.github, external: true },
      { label: "Discord", href: SITE.discord, external: true },
      { label: "Changelog", href: "/changelog" },
    ],
  },
  {
    title: "Account",
    links: [
      { label: "Sign in", href: "/login" },
      { label: "Get started", href: "/register" },
      { label: "Personal tokens", href: "/settings/tokens" },
    ],
  },
  {
    title: "Legal",
    links: [
      { label: "MIT License", href: `${SITE.github}/blob/main/LICENSE`, external: true },
      { label: "Privacy", href: "/privacy" },
      { label: "Terms", href: "/terms" },
      { label: "Cookies", href: "/cookies" },
    ],
  },
];

export function Footer() {
  return (
    <footer className="border-t border-border bg-muted/20">
      <div className="mx-auto max-w-7xl px-6 lg:px-8">
        <div className="grid gap-10 py-14 md:grid-cols-12 md:gap-8">
          {/* Brand column — wider on desktop */}
          <div className="md:col-span-5">
            <Link href="/" className="flex items-center gap-2.5">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                <Bot className="h-4 w-4" />
              </div>
              <span className="text-base font-bold tracking-tight">{SITE.name}</span>
            </Link>
            <p className="mt-4 max-w-sm text-sm leading-relaxed text-muted-foreground">
              {SITE.description}
            </p>
            <div className="mt-5 flex flex-wrap items-center gap-2">
              <a
                href={SITE.github}
                target="_blank"
                rel="noreferrer noopener"
                className="inline-flex items-center gap-2 rounded-lg border border-border bg-background px-3 py-1.5 text-xs font-medium text-foreground transition-colors hover:bg-muted"
              >
                <GithubIcon className="h-3.5 w-3.5" />
                Star on GitHub
              </a>
              <a
                href={SITE.discord}
                target="_blank"
                rel="noreferrer noopener"
                className="inline-flex items-center gap-2 rounded-lg border border-border bg-background px-3 py-1.5 text-xs font-medium text-foreground transition-colors hover:bg-muted"
              >
                Discord
              </a>
            </div>
          </div>

          {/* Link columns — 4 cols within remaining 7/12 */}
          <div className="grid gap-8 sm:grid-cols-2 md:col-span-7 md:grid-cols-4 md:gap-6">
            {COLUMNS.map((col) => (
              <div key={col.title}>
                <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  {col.title}
                </h3>
                <ul className="mt-4 space-y-2.5">
                  {col.links.map((l) => (
                    <li key={l.label}>
                      {"external" in l && l.external ? (
                        <a
                          href={l.href}
                          target="_blank"
                          rel="noreferrer noopener"
                          className="text-sm text-foreground/80 transition-colors hover:text-foreground"
                        >
                          {l.label}
                        </a>
                      ) : (
                        <Link
                          href={l.href}
                          className="text-sm text-foreground/80 transition-colors hover:text-foreground"
                        >
                          {l.label}
                        </Link>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>

        <div className="flex flex-col items-start justify-between gap-3 border-t border-border py-6 text-xs text-muted-foreground sm:flex-row sm:items-center">
          <p>© {new Date().getFullYear()} {SITE.name}. Open source, MIT licensed.</p>
          <p className="flex items-center gap-1.5">
            <span>Built with</span>
            <span className="font-medium text-foreground">FastAPI</span>
            <span>·</span>
            <span className="font-medium text-foreground">LangGraph</span>
            <span>·</span>
            <span className="font-medium text-foreground">Next.js</span>
          </p>
        </div>
      </div>
    </footer>
  );
}
