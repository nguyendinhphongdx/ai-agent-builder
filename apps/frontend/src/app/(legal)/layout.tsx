import { Footer, Nav } from "@/features/landing";

export default function LegalLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <Nav />
      <main className="mx-auto max-w-3xl px-6 py-16 lg:px-8 lg:py-20">
        {children}
      </main>
      <Footer />
    </div>
  );
}
