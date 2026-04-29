import type { Metadata } from "next";
import {
  Capabilities,
  Comparison,
  CTA,
  Footer,
  Hero,
  HowItWorks,
  IntegrationPaths,
  Nav,
  SITE,
  TrustBar,
} from "@/features/landing";

export const metadata: Metadata = {
  title: `${SITE.name} — ${SITE.tagline}`,
  description: SITE.description,
  keywords: [
    "AI agent builder",
    "open source AI agents",
    "LangGraph platform",
    "RAG",
    "MCP server",
    "AI workflow editor",
    "self-hosted AI",
    "LangChain alternative",
  ],
  authors: [{ name: SITE.name }],
  metadataBase: new URL(SITE.url),
  alternates: { canonical: SITE.url },
  openGraph: {
    title: `${SITE.name} — ${SITE.tagline}`,
    description: SITE.description,
    url: SITE.url,
    siteName: SITE.name,
    type: "website",
    locale: "en_US",
  },
  twitter: {
    card: "summary_large_image",
    title: `${SITE.name} — ${SITE.tagline}`,
    description: SITE.description,
    creator: SITE.twitter,
  },
  robots: { index: true, follow: true },
  category: "technology",
};

const JSON_LD = {
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  name: SITE.name,
  applicationCategory: "DeveloperApplication",
  operatingSystem: "Cross-platform (Docker)",
  description: SITE.description,
  url: SITE.url,
  license: `${SITE.github}/blob/main/LICENSE`,
  offers: {
    "@type": "Offer",
    price: "0",
    priceCurrency: "USD",
  },
  aggregateRating: undefined,
  author: { "@type": "Organization", name: SITE.name, url: SITE.url },
  sameAs: [SITE.github, SITE.discord],
};

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-background text-foreground selection:bg-primary/15">
      <script
        type="application/ld+json"
        // Server-rendered, safe payload constructed from constants only.
        dangerouslySetInnerHTML={{ __html: JSON.stringify(JSON_LD) }}
      />
      <Nav />
      <main>
        <Hero />
        <TrustBar />
        <Capabilities />
        <IntegrationPaths />
        <Comparison />
        <HowItWorks />
        <CTA />
      </main>
      <Footer />
    </div>
  );
}
