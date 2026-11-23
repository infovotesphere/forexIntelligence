import { Page } from "@/components/Page";
import { StrategyCatalogue } from "@/components/StrategyCatalogue";
export const instant = false;

export default function Strategies() {
  return <Page title="Strategies" description="Implemented strategy rules and signal guardrails" active="/strategies"><StrategyCatalogue /></Page>;
}
