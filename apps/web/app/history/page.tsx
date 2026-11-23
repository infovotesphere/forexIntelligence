import { Page } from "@/components/Page";
import { TradeHistoryTable } from "@/components/TradeHistoryTable";
export default function History() {
  return <Page title="Trade history" description="Recent read-only broker deal history" active="/history"><TradeHistoryTable /></Page>;
}
