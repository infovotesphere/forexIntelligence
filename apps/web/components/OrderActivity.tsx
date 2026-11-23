"use client";

import { useEffect, useState } from "react";

type Position = {
  ticket: string;
  symbol: string;
  direction: "BUY" | "SELL";
  volume: string;
  price_open: string;
  price_current: string;
  profit: string;
  stop_loss: string;
  take_profit: string;
};

type PositionResponse = {
  items: Position[];
  total: number;
  connected: boolean;
  environment: string;
  simulated: boolean;
  trading_mode: string;
};

type Deal = {
  ticket: string;
  order: string;
  symbol: string;
  direction: "BUY" | "SELL" | "OTHER";
  volume: string;
  price: string;
  profit: string;
  net_profit: string;
  time: string;
};

type HistoryResponse = {
  items: Deal[];
  total: number;
  connected: boolean;
  environment: string;
  simulated: boolean;
  period_days: number;
};

export function OrderActivity() {
  const [positions, setPositions] = useState<PositionResponse | null>(null);
  const [history, setHistory] = useState<HistoryResponse | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;

    async function refresh() {
      try {
        const [positionResponse, historyResponse] = await Promise.all([
          fetch("/api/v1/positions", { cache: "no-store" }),
          fetch("/api/v1/history", { cache: "no-store" }),
        ]);
        if (!positionResponse.ok || !historyResponse.ok) {
          throw new Error("Unable to load order activity");
        }
        const positionResult = await positionResponse.json() as PositionResponse;
        const historyResult = await historyResponse.json() as HistoryResponse;
        if (active) {
          setPositions(positionResult);
          setHistory(historyResult);
          setError("");
        }
      } catch (cause) {
        if (active) setError(cause instanceof Error ? cause.message : "Order activity unavailable");
      }
    }

    void refresh();
    const timer = window.setInterval(() => { void refresh(); }, 15000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, []);

  const openPositions = positions?.items ?? [];
  const deals = [...(history?.items ?? [])].sort((a, b) => Date.parse(b.time) - Date.parse(a.time));
  const simulated = (positions?.simulated ?? history?.simulated ?? true);

  return (
    <div>
      <section className="card history-panel">
        <div className="history-toolbar">
          <div>
            <strong>{positions?.connected ? `${positions.total} open positions` : "Broker disconnected"}</strong>
            <p>Open market activity · refreshing every 15 seconds</p>
          </div>
          <span className={`pill ${simulated ? "simulation-pill" : "broker-pill"}`}>
            {simulated ? "SIMULATION" : "MT5 · READ ONLY"}
          </span>
        </div>
        {error && <p className="error-text history-error" role="alert">{error}</p>}
        {!positions?.connected ? (
          <div className="empty history-empty">Connect an account to read open order activity.</div>
        ) : openPositions.length === 0 ? (
          <div className="empty history-empty">No open positions or pending market activity.</div>
        ) : (
          <div className="history-table-wrap">
            <table className="table history-table">
              <thead>
                <tr><th>Ticket</th><th>Instrument</th><th>Side</th><th>Volume</th><th>Open</th><th>Current</th><th>P/L</th><th>Stop</th><th>Target</th></tr>
              </thead>
              <tbody>
                {openPositions.map((position) => (
                  <tr key={position.ticket}>
                    <td>{position.ticket}</td>
                    <td><strong>{position.symbol}</strong></td>
                    <td><span className={`signal-direction ${position.direction === "BUY" ? "buy-direction" : "sell-direction"}`}>{position.direction}</span></td>
                    <td>{position.volume}</td>
                    <td>{position.price_open}</td>
                    <td>{position.price_current}</td>
                    <td className={Number(position.profit) >= 0 ? "position-profit" : "position-loss"}>{position.profit}</td>
                    <td>{Number(position.stop_loss) > 0 ? position.stop_loss : "—"}</td>
                    <td>{Number(position.take_profit) > 0 ? position.take_profit : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="card history-panel" style={{ marginTop: 12 }}>
        <div className="history-toolbar">
          <div>
            <strong>{history?.connected ? `${history.total} completed deals` : "Completed activity unavailable"}</strong>
            <p>Raw broker deals · last {history?.period_days ?? 30} days</p>
          </div>
        </div>
        {!history?.connected ? (
          <div className="empty history-empty">Connect an account to read completed deal activity.</div>
        ) : deals.length === 0 ? (
          <div className="empty history-empty">No completed broker deals were reported.</div>
        ) : (
          <div className="history-table-wrap">
            <table className="table history-table">
              <thead>
                <tr><th>Time</th><th>Deal</th><th>Order</th><th>Instrument</th><th>Side</th><th>Volume</th><th>Price</th><th>Net P/L</th></tr>
              </thead>
              <tbody>
                {deals.map((deal) => (
                  <tr key={deal.ticket}>
                    <td>{new Date(deal.time).toLocaleString()}</td>
                    <td>{deal.ticket}</td>
                    <td>{deal.order || "—"}</td>
                    <td><strong>{deal.symbol || "—"}</strong></td>
                    <td>{deal.direction}</td>
                    <td>{deal.volume}</td>
                    <td>{deal.price}</td>
                    <td className={Number(deal.net_profit) >= 0 ? "position-profit" : "position-loss"}>{deal.net_profit}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <p className="safety-note" style={{ marginTop: 12 }}>
        Read-only broker activity. This page cannot place, modify or cancel orders.
      </p>
    </div>
  );
}
