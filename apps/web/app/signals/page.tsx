import { Page } from "@/components/Page";
import { SignalsPanel } from "@/components/SignalsPanel";
export default function Signals() {
  return <Page title="Trading signals" description="Validated simulation strategy opportunities" active="/signals"><SignalsPanel /></Page>;
}
