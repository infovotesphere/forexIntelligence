"use client";

import { useEffect, useState } from "react";

type Deal = {
  ticket: string;
  order: string;
  symbol: string;
  direction: "BUY" | "SELL" | "OTHER";
  volume: string;
  price: string;
  profit: string;
  commission: string;
  swap: string;
  net_profit: string;
  time: string;
  simulated: boolean;
};

type HistoryResponse = {
  items: Deal[];
  total: number;
  connected: boolean;
  environment: string;
  currency: string;
  simulated: boolean;
  period_days: number;
  trading_mode: string;
};

export function TradeHistoryTable() {
  const [data, setData] = useState<HistoryResponse | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    async function refresh() {
      try {
        const response = await fetch("/api/v1/history", { cache: "no-store" });
        if (!response.ok) throw new Error("Unable to load broker deal history");
        const result = await response.json() as HistoryResponse;
        if (active) {
          setData(result);
          setError("");
        }
      } catch (cause) {
        if (active) setError(cause instanceof Error ? cause.message : "History service unavailable");
      }
    }

    void refresh();
    const timer = window.setInterval(() => { void refresh(); }, 15000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, []);

  const deals = [...(data?.items ?? [])].sort((a, b) => Date.parse(b.time) - Date.parse(a.time));
  const simulated = data?.simulated ?? true;

  return (
    <section className="card history-panel">
      <div className="history-toolbar">
        <div>
          <strong>{data?.connected ? `${data.total} broker deals · last ${data.period_days} days` : "Broker disconnected"}</strong>
          <p>Raw broker deal history · refreshing every 15 seconds</p>
        </div>
        <span className={`pill ${simulated ? "simulation-pill" : "broker-pill"}`}>
          {simulated ? "SIMULATION" : "MT5 · READ ONLY"}
        </span>
      </div>
      {error && <p className="error-text history-error" role="alert">{error}</p>}
      {!data?.connected ? (
        <div className="empty history-empty">Connect an MT5 account to read its recent broker deals.</div>
      ) : deals.length === 0 ? (
        <div className="empty history-empty">No broker deals were reported for the last {data.period_days} days.</div>
      ) : (
        <div className="history-table-wrap">
          <table className="table history-table">
            <thead>
              <tr><th>Time</th><th>Deal</th><th>Order</th><th>Instrument</th><th>Type</th><th>Volume</th><th>Price</th><th>Profit</th><th>Commission</th><th>Swap</th><th>Net</th></tr>
            </thead>
            <tbody>
              {deals.map((deal) => (
                <tr key={deal.ticket}>
                  <td>{new Date(deal.time).toLocaleString()}</td>
                  <td>{deal.ticket}</td>
                  <td>{deal.order || "—"}</td>
                  <td>{deal.symbol || "—"}</td>
                  <td>{deal.direction}</td>
                  <td>{deal.volume}</td>
                  <td>{deal.price}</td>
                  <td>{deal.profit}</td>
                  <td>{deal.commission}</td>
                  <td>{deal.swap}</td>
                  <td className={Number(deal.net_profit) >= 0 ? "position-profit" : "position-loss"}>{deal.net_profit}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p className="safety-note history-safety">
        These are raw broker deals, including any manual activity. They are not yet reconciled to this app&apos;s strategies or simulated orders.
      </p>
    </section>
  );
}
