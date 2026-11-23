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
  simulated: boolean;
};

type PositionResponse = {
  items: Position[];
  total: number;
  connected: boolean;
  environment: string;
  simulated: boolean;
  trading_mode: string;
};

export function PositionsTable() {
  const [data, setData] = useState<PositionResponse | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    async function refresh() {
      try {
        const response = await fetch("/api/v1/positions", { cache: "no-store" });
        if (!response.ok) throw new Error("Unable to load open positions");
        const result = await response.json() as PositionResponse;
        if (active) {
          setData(result);
          setError("");
        }
      } catch (cause) {
        if (active) setError(cause instanceof Error ? cause.message : "Position feed unavailable");
      }
    }

    void refresh();
    const timer = window.setInterval(() => { void refresh(); }, 5000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, []);

  const positions = data?.items ?? [];
  const simulated = data?.simulated ?? true;

  return (
    <section className="card positions-panel">
      <div className="positions-toolbar">
        <div>
          <strong>{data?.connected ? `${data.total} open ${data.total === 1 ? "position" : "positions"}` : "Broker disconnected"}</strong>
          <p>Read-only snapshot · refreshing every 5 seconds</p>
        </div>
        <span className={`pill ${simulated ? "simulation-pill" : "broker-pill"}`}>
          {simulated ? "SIMULATION" : "MT5 · READ ONLY"}
        </span>
      </div>
      {error && <p className="error-text positions-error" role="alert">{error}</p>}
      {!data?.connected ? (
        <div className="empty positions-empty">Connect a simulation or MT5 account to read its open positions.</div>
      ) : positions.length === 0 ? (
        <div className="empty positions-empty">No open broker positions.</div>
      ) : (
        <div className="positions-table-wrap">
          <table className="table positions-table">
            <thead>
              <tr><th>Ticket</th><th>Instrument</th><th>Side</th><th>Volume</th><th>Open price</th><th>Current price</th><th>Floating P/L</th><th>Stop loss</th><th>Take profit</th></tr>
            </thead>
            <tbody>
              {positions.map((position) => (
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
      <p className="safety-note positions-safety">
        Positions are displayed from the connected broker as a read-only snapshot. This page cannot modify stops or close trades.
      </p>
    </section>
  );
}
