"use client";

import { useEffect, useState } from "react";

type MarketQuote = {
  symbol: string;
  base_symbol?: string;
  description?: string;
  bid: string;
  ask: string;
  spread: string;
  time: string;
  digits?: number;
  simulated: boolean;
  execution_mode?: string;
};

export function MarketsTable() {
  const [markets, setMarkets] = useState<MarketQuote[]>([]);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    async function refresh() {
      try {
        const response = await fetch("/api/v1/markets", { cache: "no-store" });
        if (!response.ok) throw new Error("Unable to load market quotes");
        const data = await response.json() as MarketQuote[];
        if (active) {
          setMarkets(data);
          setError("");
        }
      } catch (cause) {
        if (active) setError(cause instanceof Error ? cause.message : "Market feed unavailable");
      } finally {
        if (active) setBusy(false);
      }
    }

    refresh();
    const timer = window.setInterval(refresh, 5000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, []);

  const simulated = markets.some((market) => market.simulated);

  return (
    <section className="card market-panel">
      <div className="market-toolbar">
        <div>
          <strong>{simulated ? "Simulation quotes" : "Broker quotes"}</strong>
          <p>{markets.length ? `Refreshing every 5 seconds · ${markets.length} instruments` : "Waiting for market data"}</p>
        </div>
        <span className={`pill ${simulated ? "simulation-pill" : "broker-pill"}`}>
          {simulated ? "SIMULATED" : "MT5 · READ ONLY"}
        </span>
      </div>
      {error && <p className="error-text market-error" role="alert">{error}</p>}
      {busy && markets.length === 0 ? (
        <div className="empty market-empty">Loading market quotes...</div>
      ) : markets.length === 0 ? (
        <div className="empty market-empty">
          <div><strong>No broker quotes available</strong>Connect a demo or MT5 account to see its monitored market data.</div>
        </div>
      ) : (
        <div className="market-table-wrap">
          <table className="table market-table">
            <thead>
              <tr><th>Instrument</th><th>Bid</th><th>Ask</th><th>Spread</th><th>Updated</th><th>Feed</th></tr>
            </thead>
            <tbody>
              {markets.map((market) => (
                <tr key={market.symbol}>
                  <td><strong>{market.symbol}</strong>{market.base_symbol && market.base_symbol !== market.symbol && <span className="market-base">{market.base_symbol}</span>}</td>
                  <td>{market.bid}</td>
                  <td>{market.ask}</td>
                  <td>{market.spread}</td>
                  <td>{new Date(market.time).toLocaleTimeString()}</td>
                  <td><span className={`market-feed ${market.simulated ? "simulated-feed" : "live-feed"}`}>{market.simulated ? "Simulated" : "MT5 read-only"}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p className="safety-note market-safety">
        Quotes are for monitoring and analysis only. The MT5 feed is read-only; no orders are placed from this scanner.
      </p>
    </section>
  );
}
