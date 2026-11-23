import { Page } from "@/components/Page";
import { MarketsTable } from "@/components/MarketsTable";
export default function Markets() {
  return <Page title="Market scanner" description="Live bid/ask quotes and market coverage" active="/markets"><MarketsTable /></Page>;
}
