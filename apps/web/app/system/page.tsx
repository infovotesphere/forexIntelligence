import { Page } from "@/components/Page";
import { SystemStatus } from "@/components/SystemStatus";

export const instant = false;

export default function System() {
  return (
    <Page title="System status" description="Database, Redis, broker and runtime health" active="/system">
      <SystemStatus />
    </Page>
  );
}
