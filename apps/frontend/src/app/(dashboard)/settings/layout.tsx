import { SettingsNav } from "@/features/settings/components/SettingsNav";

export default function SettingsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="mx-auto flex h-full max-w-6xl gap-6 p-6">
      <aside className="w-56 shrink-0">
        <div className="sticky top-6">
          <SettingsNav />
        </div>
      </aside>
      <div className="min-w-0 flex-1">{children}</div>
    </div>
  );
}
