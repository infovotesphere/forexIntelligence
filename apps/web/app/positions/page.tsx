import { Page } from "@/components/Page";
import { PositionsTable } from "@/components/PositionsTable";
export default function Positions() {
  return <Page title="Open positions" description="Read-only view of broker positions" active="/positions"><PositionsTable /></Page>;
}
