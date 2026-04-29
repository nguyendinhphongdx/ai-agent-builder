import { ApiTokensSection } from "@/features/settings/components/ApiTokensSection";

export const metadata = { title: "API Tokens" };

export default function Page() {
  return (
    <section>
      <header className="mb-5">
        <h1 className="font-heading text-xl font-semibold">API Tokens</h1>
        <p className="mt-1 text-xs text-muted-foreground">
          Personal access tokens for external clients calling{" "}
          <code className="rounded bg-muted px-1 py-0.5 text-[11px]">/api/external/*</code>.
          Treat each token as a password — anyone with it acts as you.
        </p>
      </header>
      <ApiTokensSection />
    </section>
  );
}
