"use client";

import { useEffect, useState } from "react";
import { startVisiblePolling } from "@/services/polling";
import { instrumentGroups } from "@/services/instruments";

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

function getMarketCategory(market: MarketQuote): string {
  const symbol = (market.base_symbol ?? market.symbol).toUpperCase();
  return instrumentGroups.find((group) => group.symbols.some((item) => item === symbol))?.label ?? "Other";
}

export function MarketsTable() {
  const [markets, setMarkets] = useState<MarketQuote[]>([]);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("All");

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

    const stopPolling = startVisiblePolling(refresh, 5000);
    return () => {
      active = false;
      stopPolling();
    };
  }, []);

  const simulated = markets.some((market) => market.simulated);
  const normalizedQuery = query.trim().toLocaleLowerCase();
  const categoryCounts = new Map<string, number>();
  for (const market of markets) {
    const marketCategory = getMarketCategory(market);
    categoryCounts.set(marketCategory, (categoryCounts.get(marketCategory) ?? 0) + 1);
  }
  const categories = [
    { label: "All", count: markets.length },
    ...instrumentGroups.map((group) => ({ label: group.label, count: categoryCounts.get(group.label) ?? 0 })),
    ...(categoryCounts.has("Other") ? [{ label: "Other", count: categoryCounts.get("Other") ?? 0 }] : []),
  ].filter((item) => item.label === "All" || item.count > 0);
  const categoryCount = categoryCounts.get(category) ?? markets.length;
  const visibleMarkets = markets.filter((market) => {
    if (category !== "All" && getMarketCategory(market) !== category) return false;
    return !normalizedQuery
      || market.symbol.toLocaleLowerCase().includes(normalizedQuery)
      || market.base_symbol?.toLocaleLowerCase().includes(normalizedQuery)
      || market.description?.toLocaleLowerCase().includes(normalizedQuery);
  });

  return (
    <section className="card market-panel">
      <div className="market-toolbar">
        <div>
          <strong>{simulated ? "Simulation quotes" : "Broker quotes"}</strong>
          <p>{markets.length ? `Live market coverage · ${markets.length} ${markets.length === 1 ? "instrument" : "instruments"}` : "Waiting for market data"}</p>
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
        <>
          <div className="market-controls">
            <label className="market-search">
              <svg viewBox="0 0 20 20" aria-hidden="true"><circle cx="8.5" cy="8.5" r="5.5" /><path d="m13 13 4 4" /></svg>
              <input
                type="search"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search instruments"
                aria-label="Search market instruments"
              />
            </label>
            <span className="market-results-count" aria-live="polite">
              {category === "All" && !normalizedQuery
                ? `${markets.length} instruments`
                : `${visibleMarkets.length} of ${categoryCount} shown`}
            </span>
          </div>
          <nav className="market-category-list" aria-label="Filter markets by asset class">
            {categories.map((item) => (
              <button
                key={item.label}
                className={`market-category-button ${category === item.label ? "selected" : ""}`}
                type="button"
                aria-pressed={category === item.label}
                onClick={() => setCategory(item.label)}
              >
                <span>{item.label}</span><strong>{item.count}</strong>
              </button>
            ))}
          </nav>
          {visibleMarkets.length ? (
            <div className="market-quote-grid">
              {visibleMarkets.map((market) => (
                <article className="market-quote-card" key={market.symbol}>
                  <header className="market-quote-header">
                    <div className="market-quote-instrument">
                      <strong>{market.symbol}</strong>
                      {market.base_symbol && market.base_symbol !== market.symbol && <span>{market.description ?? market.base_symbol}</span>}
                    </div>
                    <span className={`market-feed ${market.simulated ? "simulated-feed" : "live-feed"}`}>
                      <i />{market.simulated ? "SIM" : "MT5"}
                    </span>
                  </header>
                  <div className="market-quote-prices">
                    <div><span>Bid</span><strong>{market.bid}</strong></div>
                    <div><span>Ask</span><strong>{market.ask}</strong></div>
                  </div>
                  <footer className="market-quote-footer">
                    <span>Spread <strong>{market.spread}</strong></span>
                    <time dateTime={market.time} title={new Date(market.time).toLocaleString()}>{new Date(market.time).toLocaleTimeString()}</time>
                  </footer>
                </article>
              ))}
            </div>
          ) : (
            <div className="empty market-empty">
              No {category === "All" ? "instruments" : category.toLocaleLowerCase()} match{normalizedQuery ? ` “${query}”` : ""}. Try another filter or search.
            </div>
          )}
        </>
      )}
      <p className="safety-note market-safety">
        Quotes refresh every 5 seconds and are for monitoring only. The MT5 feed is read-only; this scanner cannot place orders.
      </p>
    </section>
  );
}
