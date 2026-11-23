import { Page } from "@/components/Page";
import { SignalsPanel } from "@/components/SignalsPanel";

export const instant = false;

export default function Signals() {
  return <Page title="Trading signals" description="Broker-aware strategy candidates from recent market candles" active="/signals"><SignalsPanel /></Page>;
}
