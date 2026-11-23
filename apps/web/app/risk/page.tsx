import { Page } from "@/components/Page";
import { RiskCalculator } from "@/components/RiskCalculator";
export const instant = false;

export default function Risk() {
  return <Page title="Risk management" description="Position sizing from account equity and protective stop distance" active="/risk"><RiskCalculator /></Page>;
}
