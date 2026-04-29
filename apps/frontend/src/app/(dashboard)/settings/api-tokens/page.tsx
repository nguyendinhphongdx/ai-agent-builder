import { ApiTokensSection } from "@/features/settings/components/ApiTokensSection";
import { SettingsPageHeader } from "@/features/settings/components/SettingsPrimitives";

export const metadata = { title: "API Tokens" };

export default function Page() {
  return (
    <div>
      <SettingsPageHeader
        title="API Tokens"
        description="Personal access tokens for external clients calling /api/external/*. Treat each token as a password — anyone with it acts as you."
      />
      <ApiTokensSection />
    </div>
  );
}
