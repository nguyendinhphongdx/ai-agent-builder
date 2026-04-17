import { Metadata } from "next";
import { SettingsView } from "@/features/settings/views/SettingsView";

export const metadata: Metadata = {
  title: "Settings | AgentForge",
};

export default function SettingsPage() {
  return <SettingsView />;
}
