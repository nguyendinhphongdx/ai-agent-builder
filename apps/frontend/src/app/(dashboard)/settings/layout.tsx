import { SettingsNav } from "@/features/settings/components/SettingsNav";

export default function SettingsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-6 p-6 lg:flex-row lg:gap-8">
      <aside className="lg:w-48 lg:shrink-0">
        <div className="lg:sticky lg:top-6">
          <SettingsNav />
        </div>
      </aside>
      <div className="min-w-0 flex-1 pb-12">{children}</div>
    </div>
  );
}
