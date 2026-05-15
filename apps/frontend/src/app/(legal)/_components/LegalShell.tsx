/**
 * Shared shell for /terms, /privacy, /cookies. Keeps typography +
 * effective-date stamping consistent so edits to one page don't
 * drift out of sync with the others.
 */
import type { Metadata } from "next";

export const LEGAL_ENTITY = {
  // Fill these after the business is formally registered. Until then
  // the pages display the placeholder strings — that's intentional so
  // a launch-with-stale-info accident is visible, not hidden.
  name: "[COMPANY_NAME]",
  shortName: "AgentForge",
  address: "[ADDRESS]",
  contactEmail: "[CONTACT_EMAIL]",
  dpoEmail: "[DPO_EMAIL]",
  registrationNumber: "[BUSINESS_REGISTRATION_NUMBER]",
  // Update on every substantive change. The footer of each page
  // surfaces this so users + auditors can see when text last moved.
  effectiveDate: "2026-05-15",
};

export function LegalHeader({
  title,
  subtitle,
}: {
  title: string;
  subtitle?: string;
}) {
  return (
    <header className="mb-10 border-b border-border pb-8">
      <h1 className="text-3xl font-bold tracking-tight md:text-4xl">{title}</h1>
      {subtitle && (
        <p className="mt-3 text-sm text-muted-foreground">{subtitle}</p>
      )}
      <p className="mt-4 text-xs text-muted-foreground">
        Effective date: <strong>{LEGAL_ENTITY.effectiveDate}</strong>
      </p>
    </header>
  );
}

export function LegalSection({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="mt-10 first:mt-0">
      <h2 className="text-xl font-semibold tracking-tight">{title}</h2>
      <div className="mt-3 space-y-3 text-sm leading-relaxed text-foreground/85 [&_a]:text-primary [&_a]:underline">
        {children}
      </div>
    </section>
  );
}

export function legalMetadata(title: string): Metadata {
  return {
    title: `${title} · ${LEGAL_ENTITY.shortName}`,
    robots: { index: true, follow: true },
  };
}
