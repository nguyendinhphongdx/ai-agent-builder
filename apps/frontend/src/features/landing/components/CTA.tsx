import Link from "next/link";
import { ArrowRight, Bot, Check } from "lucide-react";
import { SITE } from "../data/content";
import { GithubIcon } from "./icons";

const PROOFS = ["No credit card", "MIT licensed", "Self-hostable", "No telemetry"];

export function CTA() {
  return (
    <section className="border-t border-border">
      <div className="mx-auto max-w-7xl px-6 py-24 md:py-32 lg:px-8">
        <div className="relative overflow-hidden rounded-3xl bg-linear-to-br from-primary via-indigo-600 to-violet-600 p-12 text-center shadow-xl md:p-20">
          <div
            aria-hidden="true"
            className="pointer-events-none absolute left-0 top-0 h-64 w-64 -translate-x-1/2 -translate-y-1/2 rounded-full bg-white/10 blur-3xl"
          />
          <div
            aria-hidden="true"
            className="pointer-events-none absolute bottom-0 right-0 h-80 w-80 translate-x-1/3 translate-y-1/3 rounded-full bg-white/5 blur-3xl"
          />

          <div className="relative">
            <div className="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-2xl bg-white/15 ring-1 ring-white/20 backdrop-blur">
              <Bot className="h-7 w-7 text-white" />
            </div>
            <h2 className="text-3xl font-bold text-white sm:text-4xl">
              Ship your first agent today.
            </h2>
            <p className="mx-auto mt-4 max-w-lg text-base leading-relaxed text-white/75">
              Free forever, MIT licensed, and self-hostable. The cloud version is
              optional — your data, your infrastructure, your call.
            </p>

            <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
              <Link
                href="/register"
                className="inline-flex items-center justify-center gap-2 rounded-xl bg-white px-7 py-3 text-sm font-semibold text-primary shadow-lg transition-all hover:bg-white/95 hover:shadow-xl active:scale-[0.98]"
              >
                Start building free
                <ArrowRight className="h-4 w-4" />
              </Link>
              <a
                href={SITE.github}
                target="_blank"
                rel="noreferrer noopener"
                className="inline-flex items-center justify-center gap-2 rounded-xl border border-white/30 bg-white/10 px-7 py-3 text-sm font-semibold text-white backdrop-blur transition-all hover:bg-white/20"
              >
                <GithubIcon className="h-4 w-4" />
                Self-host on GitHub
              </a>
            </div>

            <div className="mt-8 flex flex-wrap justify-center gap-x-6 gap-y-2 text-sm text-white/70">
              {PROOFS.map((p) => (
                <span key={p} className="inline-flex items-center gap-1.5">
                  <Check className="h-3.5 w-3.5 text-emerald-300" />
                  {p}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
