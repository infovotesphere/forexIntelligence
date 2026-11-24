"use client";

import { useEffect, useRef, useState, type KeyboardEvent, type TouchEvent } from "react";

export type PracticePosition = {
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

type Props = {
  positions: PracticePosition[];
  onUpdated: () => void;
};

function apiError(payload: unknown, fallback: string): string {
  if (typeof payload === "object" && payload !== null && "detail" in payload) {
    const detail = payload.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      const messages = detail.flatMap((item) => (
        typeof item === "object" && item !== null && "msg" in item && typeof item.msg === "string"
          ? [item.msg]
          : []
      ));
      if (messages.length) return messages.join("; ");
    }
  }
  return fallback;
}

export function PracticePositionsManager({ positions, onUpdated }: Props) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const pressTimerRef = useRef<number | null>(null);
  const longPressHandledRef = useRef(false);
  const [selectedTickets, setSelectedTickets] = useState<Set<string>>(new Set());
  const [activePosition, setActivePosition] = useState<PracticePosition | null>(null);
  const [stopLoss, setStopLoss] = useState("");
  const [takeProfit, setTakeProfit] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);
  const selectedPositions = positions.filter((position) => selectedTickets.has(position.ticket));

  useEffect(() => () => {
    if (pressTimerRef.current !== null) window.clearTimeout(pressTimerRef.current);
  }, []);

  function openActions(position: PracticePosition) {
    setActivePosition(position);
    setStopLoss(Number(position.stop_loss) > 0 ? position.stop_loss : "");
    setTakeProfit(Number(position.take_profit) > 0 ? position.take_profit : "");
    setError("");
    if (!dialogRef.current?.open) dialogRef.current?.showModal();
    setDialogOpen(true);
  }

  function toggleSelected(ticket: string) {
    setSelectedTickets((current) => {
      const next = new Set(current);
      if (next.has(ticket)) next.delete(ticket);
      else next.add(ticket);
      return next;
    });
  }

  function handleTouchStart(event: TouchEvent<HTMLTableRowElement>, position: PracticePosition) {
    const target = event.target;
    if (target instanceof Element && target.closest("button, input, a")) return;
    longPressHandledRef.current = false;
    pressTimerRef.current = window.setTimeout(() => {
      longPressHandledRef.current = true;
      openActions(position);
    }, 500);
  }

  function cancelLongPress() {
    if (pressTimerRef.current !== null) {
      window.clearTimeout(pressTimerRef.current);
      pressTimerRef.current = null;
    }
  }

  function handleRowKeyDown(event: KeyboardEvent<HTMLTableRowElement>, position: PracticePosition) {
    if (event.target !== event.currentTarget) return;
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      openActions(position);
    }
  }

  async function modifyPosition(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!activePosition || busy) return;
    setBusy(true);
    setError("");
    try {
      const response = await fetch(`/api/v1/practice/positions/${encodeURIComponent(activePosition.ticket)}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          stop_loss: stopLoss.trim() || "0",
          take_profit: takeProfit.trim() || "0",
        }),
      });
      const payload: unknown = await response.json().catch(() => null);
      if (!response.ok) throw new Error(apiError(payload, "Position could not be modified"));
      dialogRef.current?.close();
      setActivePosition(null);
      onUpdated();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Position could not be modified");
    } finally {
      setBusy(false);
    }
  }

  async function closeSelected() {
    if (!selectedPositions.length || busy) return;
    if (!window.confirm(`Close ${selectedPositions.length} selected practice position${selectedPositions.length === 1 ? "" : "s"}?`)) return;
    setBusy(true);
    setError("");
    try {
      const response = await fetch("/api/v1/practice/positions/close-bulk", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tickets: selectedPositions.map((position) => position.ticket) }),
      });
      const payload: unknown = await response.json().catch(() => null);
      if (!response.ok) throw new Error(apiError(payload, "Selected positions could not be closed"));
      setSelectedTickets(new Set());
      onUpdated();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Selected positions could not be closed");
    } finally {
      setBusy(false);
    }
  }

  async function closeActivePosition() {
    if (!activePosition || busy) return;
    if (!window.confirm(`Close the simulated ${activePosition.direction} ${activePosition.symbol} position?`)) return;
    setBusy(true);
    setError("");
    try {
      const response = await fetch(`/api/v1/practice/positions/${encodeURIComponent(activePosition.ticket)}/close`, {
        method: "POST",
      });
      const payload: unknown = await response.json().catch(() => null);
      if (!response.ok) throw new Error(apiError(payload, "Position could not be closed"));
      dialogRef.current?.close();
      setActivePosition(null);
      setSelectedTickets((current) => {
        const next = new Set(current);
        next.delete(activePosition.ticket);
        return next;
      });
      onUpdated();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Position could not be closed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      {selectedPositions.length > 0 && (
        <div className="practice-bulk-toolbar">
          <span>{selectedPositions.length} selected</span>
          <button type="button" className="practice-bulk-close" disabled={busy} onClick={() => void closeSelected()}>
            Close selected
          </button>
          <button type="button" className="practice-selection-clear" onClick={() => setSelectedTickets(new Set())}>
            Clear
          </button>
        </div>
      )}
      {error && !dialogOpen && <p className="error-text practice-position-error" role="alert">{error}</p>}
      <div className="positions-table-wrap">
        <table className="table positions-table practice-open-table">
          <thead>
            <tr>
              <th aria-label="Select positions">
                <input
                  type="checkbox"
                  aria-label="Select all practice positions"
                  checked={positions.length > 0 && selectedPositions.length === positions.length}
                  onChange={() => setSelectedTickets(
                    selectedPositions.length === positions.length
                      ? new Set()
                      : new Set(positions.map((position) => position.ticket)),
                  )}
                />
              </th>
              <th>Instrument</th><th>Side</th><th>Volume</th><th>Open price</th><th>Current price</th><th>Floating P/L</th><th>Stop loss</th><th>Take profit</th><th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {positions.map((position) => (
              <tr
                key={position.ticket}
                className="practice-position-row"
                tabIndex={0}
                aria-label={`Manage ${position.direction} ${position.symbol} practice position`}
                aria-haspopup="dialog"
                onClick={() => {
                  if (longPressHandledRef.current) {
                    longPressHandledRef.current = false;
                    return;
                  }
                  openActions(position);
                }}
                onKeyDown={(event) => handleRowKeyDown(event, position)}
                onContextMenu={(event) => {
                  event.preventDefault();
                  openActions(position);
                }}
                onTouchStart={(event) => handleTouchStart(event, position)}
                onTouchMove={cancelLongPress}
                onTouchEnd={cancelLongPress}
                onTouchCancel={cancelLongPress}
              >
                <td onClick={(event) => event.stopPropagation()}>
                  <input
                    type="checkbox"
                    aria-label={`Select ${position.direction} ${position.symbol} position`}
                    checked={selectedTickets.has(position.ticket)}
                    onChange={() => toggleSelected(position.ticket)}
                  />
                </td>
                <td><strong>{position.symbol}</strong></td>
                <td><span className={`signal-direction ${position.direction === "BUY" ? "buy-direction" : "sell-direction"}`}>{position.direction}</span></td>
                <td>{position.volume}</td>
                <td>{position.price_open}</td>
                <td>{position.price_current}</td>
                <td className={Number(position.profit) >= 0 ? "position-profit" : "position-loss"}>{position.profit}</td>
                <td>{Number(position.stop_loss) > 0 ? position.stop_loss : "—"}</td>
                <td>{Number(position.take_profit) > 0 ? position.take_profit : "—"}</td>
                <td>
                  <button
                    className="practice-position-manage"
                    type="button"
                    aria-label={`Manage ${position.direction} ${position.symbol} position`}
                    onClick={(event) => {
                      event.stopPropagation();
                      openActions(position);
                    }}
                  >
                    Manage
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <dialog
        ref={dialogRef}
        className="practice-position-dialog"
        aria-labelledby="practice-position-title"
        onClose={() => {
          setDialogOpen(false);
          setActivePosition(null);
          setError("");
        }}
      >
        {activePosition && (
          <>
            <header className="practice-position-dialog-header">
              <div>
                <span className="practice-eyebrow">PRACTICE POSITION · {activePosition.ticket.slice(-8)}</span>
                <h2 id="practice-position-title">{activePosition.direction} {activePosition.symbol}</h2>
                <p>{activePosition.volume} lots · opened at {activePosition.price_open}</p>
              </div>
              <button type="button" className="practice-modal-close" aria-label="Close position actions" onClick={() => dialogRef.current?.close()}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden="true"><path d="m6 6 12 12M18 6 6 18" /></svg>
              </button>
            </header>
            <div className="practice-position-summary">
              <span>Current <strong>{activePosition.price_current}</strong></span>
              <span className={Number(activePosition.profit) >= 0 ? "position-profit" : "position-loss"}>Floating P/L <strong>{activePosition.profit}</strong></span>
            </div>
            <form className="practice-position-form" onSubmit={(event) => void modifyPosition(event)}>
              <div className="practice-position-fields">
                <label><span>Stop loss <small>Leave blank to remove</small></span><input type="number" min="0" step="any" value={stopLoss} onChange={(event) => setStopLoss(event.target.value)} placeholder="Not set" /></label>
                <label><span>Take profit <small>Leave blank to remove</small></span><input type="number" min="0" step="any" value={takeProfit} onChange={(event) => setTakeProfit(event.target.value)} placeholder="Not set" /></label>
              </div>
              {error && <p className="error-text practice-position-error" role="alert">{error}</p>}
              <footer className="practice-position-actions">
                <button type="submit" className="primary-button" disabled={busy}>{busy ? "Saving…" : "Modify position"}</button>
                <button type="button" className="practice-position-close" disabled={busy} onClick={() => void closeActivePosition()}>{busy ? "Working…" : "Close position"}</button>
              </footer>
            </form>
          </>
        )}
      </dialog>
    </>
  );
}
