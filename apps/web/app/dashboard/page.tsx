import { Page } from "@/components/Page";
import { ConnectionControls } from "@/components/ConnectionControls";
import { DashboardOverview } from "@/components/DashboardOverview";

export default function Dashboard() {
  return (
    <Page title="Trading overview" description="Live account and trading performance" active="/dashboard">
      <div style={{ marginBottom: 12 }}><ConnectionControls /></div>
      <DashboardOverview />
    </Page>
  );
}
