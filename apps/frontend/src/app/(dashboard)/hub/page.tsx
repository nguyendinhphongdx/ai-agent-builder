import { HubBrowseView } from "@/features/hub/views/HubBrowseView";

export const metadata = {
  title: "Hub — Browse agents",
  description: "Discover agents published by the community. Fork one to your library.",
};

export default function HubPage() {
  return <HubBrowseView />;
}
