import { Page } from "@/components/Page";
import { SettingsTabs } from "@/components/SettingsTabs";
export const instant = false;

export default function Settings() {
  return (
    <Page title="Settings" description="Broker, account and system configuration" active="/settings">
      <SettingsTabs />
    </Page>
  );
}
