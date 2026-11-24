"use client";

import { useEffect, useState } from "react";
import { SearchableSelect } from "@/components/SearchableSelect";
import { startVisiblePolling } from "@/services/polling";

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
  deal_type?: "ENTRY" | "EXIT";
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

type DirectionFilter = "ALL" | Deal["direction"];

function isDirectionFilter(value: string): value is DirectionFilter {
  return value === "ALL" || value === "BUY" || value === "SELL" || value === "OTHER";
}

export function TradeHistoryTable() {
  const [data, setData] = useState<HistoryResponse | null>(null);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [direction, setDirection] = useState<DirectionFilter>("ALL");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

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

    const stopPolling = startVisiblePolling(refresh, 15000);
    return () => {
      active = false;
      stopPolling();
    };
  }, []);

  const deals = [...(data?.items ?? [])].sort((a, b) => Date.parse(b.time) - Date.parse(a.time));
  const filteredDeals = deals.filter((deal) => {
    const query = search.trim().toLocaleLowerCase();
    const matchesSearch = !query || `${deal.symbol} ${deal.ticket} ${deal.order} ${deal.direction}`.toLocaleLowerCase().includes(query);
    return matchesSearch && (direction === "ALL" || deal.direction === direction);
  });
  const pageCount = Math.max(1, Math.ceil(filteredDeals.length / pageSize));
  const currentPage = Math.min(page, pageCount);
  const firstDeal = filteredDeals.length === 0 ? 0 : (currentPage - 1) * pageSize;
  const lastDeal = Math.min(firstDeal + pageSize, filteredDeals.length);
  const pageDeals = filteredDeals.slice(firstDeal, lastDeal);
  const simulated = data?.simulated ?? true;

  return (
    <section className="card history-panel">
      <div className="history-toolbar">
        <div>
          <strong>{data
            ? data.connected
              ? data.simulated
                ? `${data.total} practice trade events`
                : `${data.total} broker deals · last ${data.period_days} days`
              : "Broker disconnected"
            : "Loading trade history"}</strong>
          <p>{simulated
            ? "Practice entries and exits · saved to this account"
            : "Raw broker deal history · refreshing every 15 seconds"}</p>
        </div>
        <span className={`pill ${simulated ? "simulation-pill" : "broker-pill"}`}>
          {simulated ? "SIMULATION" : "MT5 · READ ONLY"}
        </span>
      </div>
      {error && <p className="error-text history-error" role="alert">{error}</p>}
      {!data ? (
        <div className="empty history-empty">{error ? "Broker history could not be loaded." : "Loading recent trade activity…"}</div>
      ) : !data.connected ? (
        <div className="empty history-empty">Connect an MT5 account to read its recent broker deals.</div>
      ) : deals.length === 0 ? (
        <div className="empty history-empty">
          {simulated
            ? "Placed practice trades will appear here and remain available after reload."
            : `No broker deals were reported for the last ${data.period_days} days.`}
        </div>
      ) : (
        <>
          <div className="history-controls">
            <label className="history-search">
              <svg viewBox="0 0 20 20" aria-hidden="true"><circle cx="8.5" cy="8.5" r="5.5" /><path d="m13 13 4 4" /></svg>
              <input
                type="search"
                value={search}
                onChange={(event) => { setSearch(event.target.value); setPage(1); }}
                placeholder="Search symbol, ticket, or side"
                aria-label="Search trade history"
              />
            </label>
            <label className="history-direction-filter">
              <span>Side</span>
              <SearchableSelect value={direction} onChange={(value) => {
                if (isDirectionFilter(value)) setDirection(value);
                setPage(1);
              }} options={[
                { value: "ALL", label: "All sides" },
                { value: "BUY", label: "Buy" },
                { value: "SELL", label: "Sell" },
                { value: "OTHER", label: "Other" },
              ]} ariaLabel="Trade side" className="compact" />
            </label>
            <span className="history-results-count">{filteredDeals.length} {filteredDeals.length === 1 ? "deal" : "deals"}</span>
          </div>
          {filteredDeals.length === 0 ? (
            <div className="empty history-empty">No deals match your search and side filters.</div>
          ) : (
            <>
              <div className="history-table-wrap">
                <table className="table history-table">
                  <thead>
                    <tr><th>Date / Deal / Order</th><th>Instrument</th><th>Side</th><th>Execution</th><th>Volume</th><th>Price</th><th>Profit</th><th>Commission</th><th>Swap</th><th>Net</th></tr>
                  </thead>
                  <tbody>
                    {pageDeals.map((deal) => (
                      <tr key={deal.ticket}>
                        <td className="history-record-cell">
                          <div className="history-record-stack">
                            <time className="history-record-date" dateTime={deal.time}>{new Date(deal.time).toLocaleString()}</time>
                            <div className="history-record-meta"><span>Deal</span><strong>{deal.ticket}</strong></div>
                            <div className="history-record-meta"><span>Order</span><strong>{deal.order || "—"}</strong></div>
                          </div>
                        </td>
                        <td>{deal.symbol || "—"}</td>
                        <td><span className={`signal-direction ${deal.direction === "BUY" ? "buy-direction" : deal.direction === "SELL" ? "sell-direction" : ""}`}>{deal.direction}</span></td>
                        <td>{deal.deal_type ?? "DEAL"}</td>
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
              <nav className="history-pagination" aria-label="Trade history pages">
                <p aria-live="polite">Showing <strong>{firstDeal + 1}–{lastDeal}</strong> of <strong>{filteredDeals.length}</strong> deals</p>
                <div className="history-pagination-controls">
                  <label>
                    <span>Rows</span>
                    <SearchableSelect
                      value={String(pageSize)}
                      onChange={(value) => {
                        const size = Number(value);
                        if ([10, 20, 50].includes(size)) {
                          setPageSize(size);
                          setPage(1);
                        }
                      }}
                      options={[10, 20, 50].map((item) => ({ value: String(item), label: String(item) }))}
                      ariaLabel="Trade history rows per page"
                      className="compact"
                    />
                  </label>
                  <button type="button" className="history-page-button" onClick={() => setPage(currentPage - 1)} disabled={currentPage === 1} aria-label="Previous page">
                    <svg viewBox="0 0 20 20" aria-hidden="true"><path d="m12 4-6 6 6 6" /></svg>
                  </button>
                  <span className="history-page-indicator">Page {currentPage} of {pageCount}</span>
                  <button type="button" className="history-page-button" onClick={() => setPage(currentPage + 1)} disabled={currentPage === pageCount} aria-label="Next page">
                    <svg viewBox="0 0 20 20" aria-hidden="true"><path d="m8 4 6 6-6 6" /></svg>
                  </button>
                </div>
              </nav>
            </>
          )}
        </>
      )}
      <p className="safety-note history-safety">
        {simulated
          ? "Practice events are virtual executions; they do not represent broker orders."
          : "These are raw broker deals, including any manual activity. They are not yet reconciled to this app&apos;s strategies or simulated orders."}
      </p>
    </section>
  );
}
