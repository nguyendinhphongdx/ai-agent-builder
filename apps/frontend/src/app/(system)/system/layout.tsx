import { SystemLayout } from "@/features/system/components/SystemLayout";

export default function Layout({ children }: { children: React.ReactNode }) {
  return <SystemLayout>{children}</SystemLayout>;
}
