import { Page } from "@/components/Page";
import { MarketsTable } from "@/components/MarketsTable";
export const instant = false;

export default function Markets() {
  return <Page title="Market scanner" description="Live bid/ask quotes and market coverage" active="/markets"><MarketsTable /></Page>;
}
