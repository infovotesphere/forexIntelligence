import { Suspense } from "react";
import { Page } from "@/components/Page";
import { BacktestRunner } from "@/components/BacktestRunner";

export const instant = false;

export default function Backtesting() {
  return <Page title="Backtesting" description="Simulation replay of strategy rules" active="/backtesting"><Suspense fallback={<div className="card">Loading backtest controls...</div>}><BacktestRunner /></Suspense></Page>;
}
