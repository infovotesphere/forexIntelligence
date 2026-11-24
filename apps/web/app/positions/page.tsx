import { Page } from "@/components/Page";
import { PositionsTable } from "@/components/PositionsTable";

export const instant = false;

export default function Positions() {
  return <Page title="Positions & market monitor" description="Track candlesticks, paper trades, and read-only broker positions" active="/positions"><PositionsTable /></Page>;
}
