import { Page } from "@/components/Page";
import { TechnicalAnalysis } from "@/components/TechnicalAnalysis";
export default function Analytics() {
  return <Page title="Market analytics" description="Technical indicators and strategy context" active="/analytics"><TechnicalAnalysis /></Page>;
}
