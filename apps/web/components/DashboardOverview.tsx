"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { DashboardPerformance } from "./DashboardPerformance";

type AccountStatus = {
  connected: boolean;
  broker: string;
  environment: string;
  engine_running: boolean;
  simulated: boolean;
  message: string;
  account?: { currency: string; balance: string | null; equity: string | null } | null;
};

type MarketQuote = { symbol: string; bid: string; ask: string; spread: string; simulated: boolean };
type Signal = { signal_id?: string; symbol: string; direction?: string; strategy: string; status: string; created_at: string };

export function DashboardOverview() {
  const [account, setAccount] = useState<AccountStatus | null>(null);
  const [markets, setMarkets] = useState<MarketQuote[]>([]);
  const [signals, setSignals] = useState<Signal[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    async function refresh() {
      try {
        const [accountResponse, marketResponse, signalResponse] = await Promise.all([
          fetch("/api/v1/accounts/status", { cache: "no-store" }),
          fetch("/api/v1/markets", { cache: "no-store" }),
          fetch("/api/v1/signals", { cache: "no-store" }),
        ]);
        if (!accountResponse.ok || !marketResponse.ok || !signalResponse.ok) {
          throw new Error("Unable to refresh dashboard data");
        }
        const [accountData, marketData, signalData] = await Promise.all([
          accountResponse.json() as Promise<AccountStatus>,
          marketResponse.json() as Promise<MarketQuote[]>,
          signalResponse.json() as Promise<{ items: Signal[] }>,
        ]);
        if (active) {
          setAccount(accountData);
          setMarkets(marketData);
          setSignals(signalData.items);
          setError("");
        }
      } catch (cause) {
        if (active) setError(cause instanceof Error ? cause.message : "Dashboard data unavailable");
      }
    }

    void refresh();
    const timer = window.setInterval(() => { void refresh(); }, 10000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, []);

  const accountLabel = !account?.connected
    ? "Disconnected"
    : account.broker === "mt5"
      ? account.environment === "live" ? "MT5 live · read-only" : "MT5 demo"
      : "Simulation demo";
  const activeSignals = signals.filter((signal) => signal.status === "VALIDATED").length;
  const recentSignals = [...signals].reverse().slice(0, 5);

  return (
    <>
      {error && <p className="error-text dashboard-error" role="alert">{error}</p>}
      <section className="grid metrics dashboard-metrics" aria-label="Account overview">
        <div className="card metric"><div className="metric-label">Account balance</div><div className="metric-value">{account?.account?.balance ? `${account.account.currency} ${account.account.balance}` : "—"}</div></div>
        <div className="card metric"><div className="metric-label">Account equity</div><div className="metric-value">{account?.account?.equity ? `${account.account.currency} ${account.account.equity}` : "—"}</div></div>
        <div className="card metric"><div className="metric-label">Broker</div><div className="metric-value dashboard-small-value">{accountLabel}</div></div>
        <div className="card metric"><div className="metric-label">Trading engine</div><div className="metric-value dashboard-small-value">{account?.engine_running ? "Running · paper" : account?.environment === "live" ? "Read-only" : "Stopped"}</div></div>
      </section>

      <DashboardPerformance />

      <section className="grid two-col">
        <div className="card panel dashboard-panel">
          <div className="dashboard-panel-heading"><h2>Market quotes</h2><Link href="/markets">Open scanner</Link></div>
          {markets.length ? (
            <div className="dashboard-table-wrap">
              <table className="table"><thead><tr><th>Instrument</th><th>Bid</th><th>Ask</th><th>Feed</th></tr></thead>
                <tbody>{markets.slice(0, 5).map((market) => <tr key={market.symbol}><td>{market.symbol}</td><td>{market.bid}</td><td>{market.ask}</td><td>{market.simulated ? "Simulation" : "MT5"}</td></tr>)}</tbody>
              </table>
            </div>
          ) : <div className="dashboard-empty">{account?.broker === "mt5" ? "Waiting for MT5 quotes" : "No quotes available"}</div>}
        </div>
        <div className="card panel dashboard-panel">
          <div className="dashboard-panel-heading"><h2>Recent signals</h2><Link href="/signals">View signals</Link></div>
          {recentSignals.length ? (
            <div className="dashboard-table-wrap">
              <table className="table"><thead><tr><th>Market</th><th>Direction</th><th>Strategy</th><th>Status</th></tr></thead>
                <tbody>{recentSignals.map((signal, index) => <tr key={signal.signal_id ?? `${signal.symbol}-${index}`}><td>{signal.symbol}</td><td>{signal.direction ?? "—"}</td><td>{signal.strategy}</td><td>{signal.status}</td></tr>)}</tbody>
              </table>
            </div>
          ) : <div className="dashboard-empty">No signals generated yet.</div>}
          <div className="dashboard-signal-count">{activeSignals} validated · signals are simulation-only</div>
        </div>
      </section>
    </>
  );
}
