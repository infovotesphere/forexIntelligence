import { Page } from "@/components/Page";
import { NotificationSettings } from "@/components/NotificationSettings";

export const instant = false;

export default function Notifications() {
  return (
    <Page title="Notifications" description="Telegram delivery configuration" active="/notifications">
      <NotificationSettings />
    </Page>
  );
}
