"use client";

import { useEffect, useRef, useState } from "react";
import { startVisiblePolling } from "@/services/polling";
import { SimulationTradeTicket } from "@/components/SimulationTradeTicket";

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
  simulated?: boolean;
};

type PositionResponse = {
  items: Position[];
  total: number;
  connected: boolean;
  broker: string;
  can_trade_simulation: boolean;
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
  simulated?: boolean;
  deal_type?: "ENTRY" | "EXIT";
};

type HistoryResponse = {
  items: Deal[];
  total: number;
  connected: boolean;
  environment: string;
  simulated: boolean;
  period_days: number;
};

type PracticePositionsResponse = {
  items: Position[];
  total: number;
  pending_orders: PendingOrder[];
  pending_total: number;
  account: { currency: string; balance: string; equity: string };
};

type PendingOrder = {
  ticket: string;
  symbol: string;
  order_type: "BUY_STOP" | "SELL_STOP";
  direction: "BUY" | "SELL";
  volume: string;
  stop_price: string;
  stop_loss: string;
  take_profit: string;
  created_at: string;
};

type PracticeHistoryResponse = {
  items: Deal[];
  total: number;
};

type ActivitySection = "practice" | "pending" | "broker" | "practice-history" | "broker-history";

export function OrderActivity() {
  const [positions, setPositions] = useState<PositionResponse | null>(null);
  const [history, setHistory] = useState<HistoryResponse | null>(null);
  const [practicePositions, setPracticePositions] = useState<PracticePositionsResponse | null>(null);
  const [practiceHistory, setPracticeHistory] = useState<PracticeHistoryResponse | null>(null);
  const [activeSection, setActiveSection] = useState<ActivitySection>("practice");
  const [error, setError] = useState("");
  const [busyTicket, setBusyTicket] = useState("");
  const [refreshVersion, setRefreshVersion] = useState(0);
  const [pendingCancellation, setPendingCancellation] = useState<PendingOrder | null>(null);
  const [cancelError, setCancelError] = useState("");
  const cancelDialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = cancelDialogRef.current;
    if (!dialog) return;
    if (pendingCancellation && !dialog.open) dialog.showModal();
    if (!pendingCancellation && dialog.open) dialog.close();
  }, [pendingCancellation]);

  useEffect(() => {
    let active = true;

    async function refresh() {
      try {
        const [positionResponse, historyResponse, practicePositionResponse, practiceHistoryResponse] = await Promise.all([
          fetch("/api/v1/positions", { cache: "no-store" }),
          fetch("/api/v1/history", { cache: "no-store" }),
          fetch("/api/v1/practice/positions", { cache: "no-store" }),
          fetch("/api/v1/practice/history", { cache: "no-store" }),
        ]);
        if (!positionResponse.ok || !historyResponse.ok || !practicePositionResponse.ok || !practiceHistoryResponse.ok) {
          throw new Error("Unable to load order activity");
        }
        const positionResult = await positionResponse.json() as PositionResponse;
        const historyResult = await historyResponse.json() as HistoryResponse;
        const practicePositionResult = await practicePositionResponse.json() as PracticePositionsResponse;
        const practiceHistoryResult = await practiceHistoryResponse.json() as PracticeHistoryResponse;
        if (active) {
          setPositions(positionResult);
          setHistory(historyResult);
          setPracticePositions(practicePositionResult);
          setPracticeHistory(practiceHistoryResult);
          setError("");
        }
      } catch (cause) {
        if (active) setError(cause instanceof Error ? cause.message : "Order activity unavailable");
      }
    }

    const stopPolling = startVisiblePolling(refresh, 15000);
    return () => {
      active = false;
      stopPolling();
    };
  }, [refreshVersion]);

  async function closePracticeTrade(position: Position) {
    if (!window.confirm(`Close the simulated ${position.direction} ${position.symbol} position?`)) return;
    setBusyTicket(position.ticket);
    setError("");
    try {
      const response = await fetch(`/api/v1/practice/positions/${encodeURIComponent(position.ticket)}/close`, { method: "POST" });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail ?? "Practice trade could not be closed");
      setRefreshVersion((version) => version + 1);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Practice trade could not be closed");
    } finally {
      setBusyTicket("");
    }
  }

  async function cancelPendingOrder(order: PendingOrder) {
    setBusyTicket(order.ticket);
    setCancelError("");
    try {
      const response = await fetch(`/api/v1/practice/orders/${encodeURIComponent(order.ticket)}`, { method: "DELETE" });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail ?? "Pending order could not be cancelled");
      setRefreshVersion((version) => version + 1);
      setPendingCancellation(null);
    } catch (cause) {
      setCancelError(cause instanceof Error ? cause.message : "Pending order could not be cancelled");
    } finally {
      setBusyTicket("");
    }
  }

  function requestCancelPendingOrder(order: PendingOrder) {
    setCancelError("");
    setPendingCancellation(order);
  }

  const openPositions = (positions?.items ?? []).filter((position) => !position.simulated);
  const deals = [...(history?.items ?? [])]
    .filter((deal) => !deal.simulated)
    .sort((a, b) => Date.parse(b.time) - Date.parse(a.time));
  const simulated = (positions?.simulated ?? history?.simulated ?? true);
  const activitySections: { id: ActivitySection; label: string; count: number }[] = [
    { id: "practice", label: "Practice positions", count: practicePositions?.total ?? 0 },
    { id: "pending", label: "Pending orders", count: practicePositions?.pending_total ?? 0 },
    { id: "broker", label: "Broker positions", count: openPositions.length },
    { id: "practice-history", label: "Practice history", count: practiceHistory?.total ?? 0 },
    { id: "broker-history", label: "Broker history", count: deals.length },
  ];

  return (
    <div className="order-activity">
      <SimulationTradeTicket
        onSubmitted={() => setRefreshVersion((version) => version + 1)}
      />
      <nav className="activity-tabs" aria-label="Order activity sections">
        {activitySections.map((section) => (
          <button
            key={section.id}
            className={`activity-tab${activeSection === section.id ? " activity-tab-active" : ""}`}
            type="button"
            aria-pressed={activeSection === section.id}
            onClick={() => setActiveSection(section.id)}
          >
            <span>{section.label}</span>
            <span className="activity-tab-count">{section.count}</span>
          </button>
        ))}
      </nav>
      {error && <p className="error-text history-error" role="alert">{error}</p>}
      <section className="card history-panel" hidden={activeSection !== "broker"}>
        <div className="history-toolbar">
          <div>
            <strong>{positions?.connected ? `${openPositions.length} open ${openPositions.length === 1 ? "position" : "positions"}` : "Broker disconnected"}</strong>
            <p>Broker account positions · refreshing every 15 seconds</p>
          </div>
          <span className={`pill ${simulated ? "simulation-pill" : "broker-pill"}`}>
            {simulated ? "SIMULATION" : "MT5 · READ ONLY"}
          </span>
        </div>
        {!positions?.connected ? (
          <div className="empty history-empty">Connect an account to read open order activity.</div>
        ) : openPositions.length === 0 ? (
          <div className="empty history-empty">No open broker positions or pending market activity.</div>
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

      <section className="card history-panel" hidden={activeSection !== "practice"}>
        <div className="history-toolbar">
          <div>
            <strong>{practicePositions?.account.currency ?? "USD"} {practicePositions?.account.balance ?? "—"} practice balance</strong>
            <p>{practicePositions?.total ?? 0} open virtual positions · independent of your broker account</p>
          </div>
          <span className="pill simulation-pill">PRACTICE ONLY</span>
        </div>
        {!practicePositions ? (
          <div className="empty history-empty">Loading the independent practice account…</div>
        ) : practicePositions.items.length === 0 ? (
          <div className="empty history-empty">No open practice positions yet. Select “Place a trade” above to start.</div>
        ) : (
          <div className="history-table-wrap">
            <table className="table history-table">
              <thead>
                <tr><th>Ticket</th><th>Instrument</th><th>Side</th><th>Volume</th><th>Open</th><th>Current</th><th>P/L</th><th>Stop</th><th>Target</th><th>Action</th></tr>
              </thead>
              <tbody>
                {practicePositions.items.map((position) => (
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
                    <td>
                      <button className="practice-close-button" type="button" aria-label={`Close ${position.direction} ${position.symbol} position`} disabled={busyTicket === position.ticket} onClick={() => void closePracticeTrade(position)}>
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M5 5h14v14H5z" /><path d="m9 9 6 6m0-6-6 6" /></svg>
                        <span>{busyTicket === position.ticket ? "Closing…" : "Close"}</span>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="card history-panel" hidden={activeSection !== "pending"}>
        <div className="history-toolbar">
          <div>
            <strong>{practicePositions?.pending_total ?? 0} pending stop orders</strong>
            <p>Buy stops trigger above market; sell stops trigger below market</p>
          </div>
        </div>
        {!practicePositions ? (
          <div className="empty history-empty">Loading pending practice orders…</div>
        ) : practicePositions.pending_orders.length === 0 ? (
          <div className="empty history-empty">Pending buy stop and sell stop orders will appear here.</div>
        ) : (
          <div className="history-table-wrap">
            <table className="table history-table">
              <thead><tr><th>Order</th><th>Instrument</th><th>Side</th><th>Volume</th><th>Trigger</th><th>Stop</th><th>Target</th><th>Action</th></tr></thead>
              <tbody>
                {practicePositions.pending_orders.map((order) => (
                  <tr key={order.ticket}>
                    <td>{order.order_type.replace("_", " ")}</td>
                    <td><strong>{order.symbol}</strong></td>
                    <td>{order.direction}</td>
                    <td>{order.volume}</td>
                    <td>{order.stop_price}</td>
                    <td>{Number(order.stop_loss) > 0 ? order.stop_loss : "—"}</td>
                    <td>{Number(order.take_profit) > 0 ? order.take_profit : "—"}</td>
                    <td>
                      <button className="practice-close-button" type="button" aria-label={`Cancel ${order.order_type.replace("_", " ")} ${order.symbol}`} title="Cancel pending order" disabled={busyTicket === order.ticket} onClick={() => requestCancelPendingOrder(order)}>
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden="true"><path d="m6 6 12 12M18 6 6 18" /></svg>
                        <span>{busyTicket === order.ticket ? "Cancelling…" : "Cancel"}</span>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="card history-panel" hidden={activeSection !== "broker-history"}>
        <div className="history-toolbar">
          <div>
            <strong>{history?.connected ? `${deals.length} completed broker deals` : "Completed broker activity unavailable"}</strong>
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
                <tr><th>Date / Deal / Order</th><th>Instrument</th><th>Side</th><th>Volume</th><th>Price</th><th>Net P/L</th></tr>
              </thead>
              <tbody>
                {deals.map((deal) => (
                  <tr key={deal.ticket}>
                    <td className="history-record-cell">
                      <div className="history-record-stack">
                        <time className="history-record-date" dateTime={deal.time}>{new Date(deal.time).toLocaleString()}</time>
                        <div className="history-record-meta"><span>Deal</span><strong>{deal.ticket}</strong></div>
                        <div className="history-record-meta"><span>Order</span><strong>{deal.order || "—"}</strong></div>
                      </div>
                    </td>
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

      <section className="card history-panel" hidden={activeSection !== "practice-history"}>
        <div className="history-toolbar">
          <div>
            <strong>{practiceHistory?.total ?? 0} practice trade events</strong>
            <p>Virtual entries and exits · isolated from broker activity</p>
          </div>
        </div>
        {!practiceHistory ? (
          <div className="empty history-empty">Loading practice history…</div>
        ) : practiceHistory.items.length === 0 ? (
          <div className="empty history-empty">Placed practice trades will appear here as entry and exit events.</div>
        ) : (
          <div className="history-table-wrap">
            <table className="table history-table">
              <thead><tr><th>Date / Deal / Order</th><th>Instrument</th><th>Side</th><th>Execution</th><th>Volume</th><th>Price</th><th>Net P/L</th></tr></thead>
              <tbody>
                {practiceHistory.items.map((deal) => (
                  <tr key={deal.ticket}>
                    <td className="history-record-cell">
                      <div className="history-record-stack">
                        <time className="history-record-date" dateTime={deal.time}>{new Date(deal.time).toLocaleString()}</time>
                        <div className="history-record-meta"><span>Deal</span><strong>{deal.ticket}</strong></div>
                        <div className="history-record-meta"><span>Order</span><strong>{deal.order || "—"}</strong></div>
                      </div>
                    </td>
                    <td><strong>{deal.symbol || "—"}</strong></td>
                    <td>{deal.direction}</td>
                    <td>{deal.deal_type ?? "DEAL"}</td>
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
        Practice trades use an isolated virtual account. Broker positions remain read-only; MT5 receives no practice orders.
      </p>
      <dialog
        ref={cancelDialogRef}
        className="order-cancel-dialog"
        aria-labelledby="order-cancel-dialog-title"
        onCancel={(event) => {
          event.preventDefault();
          if (busyTicket) return;
          setPendingCancellation(null);
          setCancelError("");
        }}
      >
        {pendingCancellation && (
          <div className="order-cancel-shell">
            <header className="order-cancel-header">
              <span className="order-cancel-icon" aria-hidden="true">
                <svg viewBox="0 0 24 24"><path d="M5 7h14M9 7V4h6v3m-8 0 1 13h8l1-13M10 11v5m4-5v5" /></svg>
              </span>
              <div>
                <span className="system-eyebrow">Pending order action</span>
                <h2 id="order-cancel-dialog-title">Cancel this order?</h2>
                <p>Review the order details before confirming.</p>
              </div>
              <button className="modal-close" type="button" aria-label="Close cancellation dialog" disabled={Boolean(busyTicket)} onClick={() => { setPendingCancellation(null); setCancelError(""); }}>×</button>
            </header>
            <div className="order-cancel-details">
              <div className="order-cancel-instrument">
                <span>{pendingCancellation.symbol}</span>
                <strong className={pendingCancellation.direction === "BUY" ? "buy-direction" : "sell-direction"}>{pendingCancellation.order_type.replaceAll("_", " ")}</strong>
              </div>
              <dl>
                <div><dt>Order ID</dt><dd>{pendingCancellation.ticket}</dd></div>
                <div><dt>Volume</dt><dd>{pendingCancellation.volume}</dd></div>
                <div><dt>Trigger price</dt><dd>{pendingCancellation.stop_price}</dd></div>
              </dl>
              <p className="order-cancel-notice">This removes the pending practice order only. No broker order will be changed.</p>
            </div>
            {cancelError && <p className="error-text order-cancel-error" role="alert">{cancelError}</p>}
            <footer className="order-cancel-actions">
              <button className="secondary-button" type="button" disabled={Boolean(busyTicket)} onClick={() => { setPendingCancellation(null); setCancelError(""); }}>Keep order</button>
              <button className="danger-button" type="button" disabled={Boolean(busyTicket)} onClick={() => void cancelPendingOrder(pendingCancellation)}>
                {busyTicket === pendingCancellation.ticket ? "Cancelling…" : "Cancel order"}
              </button>
            </footer>
          </div>
        )}
      </dialog>
    </div>
  );
}
