import { Page } from "@/components/Page";
import { BacktestRunner } from "@/components/BacktestRunner";
export default function Backtesting() {
  return <Page title="Backtesting" description="Simulation replay of strategy rules" active="/backtesting"><BacktestRunner /></Page>;
}
