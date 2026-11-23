"use client";

import { type FormEvent, useEffect, useState } from "react";

type Signal = {
  signal_id?: string;
  symbol: string;
  direction?: "BUY" | "SELL";
  strategy: string;
  timeframe: string;
  entry?: string;
  stop_loss?: string;
  tp1?: string;
  tp2?: string;
  tp3?: string;
  risk_reward_ratio?: string;
  quality_score?: number;
  explanation?: string;
  rejection_reason?: string;
  status: "VALIDATED" | "REJECTED" | "EXPIRED";
  created_at: string;
  expires_at?: string;
};

const symbols = ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "USDCAD", "AUDUSD", "NZDUSD", "XAUUSD"];
const timeframes = ["M5", "M15", "M30", "H1", "H4", "D1"];

export function SignalsPanel() {
  const [signals, setSignals] = useState<Signal[]>([]);
  const [symbol, setSymbol] = useState("EURUSD");
  const [timeframe, setTimeframe] = useState("H1");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    async function loadSignals() {
      try {
        const response = await fetch("/api/v1/signals", { cache: "no-store" });
        if (!response.ok) throw new Error("Unable to load trading signals");
        const result = await response.json() as { items: Signal[] };
        if (active) {
          setSignals(result.items);
          setError("");
        }
      } catch (cause) {
        if (active) setError(cause instanceof Error ? cause.message : "Signal service unavailable");
      } finally {
        if (active) setLoading(false);
      }
    }

    void loadSignals();
    const timer = window.setInterval(loadSignals, 30000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, []);

  async function generate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const params = new URLSearchParams({ symbol, timeframe });
      const response = await fetch(`/api/v1/signals/generate?${params}`, { method: "POST" });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail ?? "Signal generation failed");
      const listResponse = await fetch("/api/v1/signals", { cache: "no-store" });
      if (!listResponse.ok) throw new Error("Signals generated, but could not refresh the signal list");
      const list = await listResponse.json() as { items: Signal[] };
      setSignals(list.items);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Signal generation failed");
    } finally {
      setBusy(false);
    }
  }

  const validatedCount = signals.filter((signal) => signal.status === "VALIDATED").length;
  const expiredCount = signals.filter((signal) => signal.status === "EXPIRED").length;

  return (
    <div className="signals-content">
      <div className="signal-warning" role="note">
        <strong>Simulation only</strong>
        <span>Signals use generated simulation candles, not MT5 market history. They are informational and never place orders.</span>
      </div>
      <section className="card panel signal-controls">
        <div>
          <h2>Generate opportunities</h2>
          <p>Strategy candidates are validated for a protective stop and minimum 1:2 reward/risk.</p>
        </div>
        <form className="signal-form" onSubmit={generate}>
          <label>
            <span>Instrument</span>
            <select value={symbol} onChange={(event) => setSymbol(event.target.value)}>
              {symbols.map((item) => <option key={item} value={item}>{item}</option>)}
            </select>
          </label>
          <label>
            <span>Timeframe</span>
            <select value={timeframe} onChange={(event) => setTimeframe(event.target.value)}>
              {timeframes.map((item) => <option key={item} value={item}>{item}</option>)}
            </select>
          </label>
          <button className="primary-button" type="submit" disabled={busy}>
            {busy ? "Analyzing..." : "Generate signals"}
          </button>
        </form>
        {error && <p className="error-text" role="alert">{error}</p>}
      </section>

      <section className="card signal-list">
        <div className="signal-list-heading">
          <div><h2>Recent signals</h2><p>{validatedCount} active · {expiredCount} expired</p></div>
          <span className="pill">In-memory · simulation</span>
        </div>
        {loading && signals.length === 0 ? (
          <div className="empty signal-empty">Loading signals...</div>
        ) : signals.length === 0 ? (
          <div className="empty signal-empty">No signals yet. Generate candidates to get started.</div>
        ) : (
          <div className="signal-table-wrap">
            <table className="table signal-table">
              <thead>
                <tr><th>Market</th><th>Direction</th><th>Entry / stop</th><th>Targets</th><th>R:R (TP3)</th><th>Quality</th><th>Status</th><th>Details</th></tr>
              </thead>
              <tbody>
                {signals.map((signal, index) => (
                  <tr key={signal.signal_id ?? `${signal.symbol}-${signal.created_at}-${index}`}>
                    <td><strong>{signal.symbol}</strong><span className="signal-meta">{signal.strategy} · {signal.timeframe}</span></td>
                    <td><span className={`signal-direction ${signal.direction === "BUY" ? "buy-direction" : signal.direction === "SELL" ? "sell-direction" : ""}`}>{signal.direction ?? "—"}</span></td>
                    <td>{signal.entry ? <>{signal.entry}<span className="signal-meta">SL {signal.stop_loss}</span></> : "—"}</td>
                    <td>{signal.tp1 ? <>{signal.tp1}<span className="signal-meta">TP2 {signal.tp2} · TP3 {signal.tp3}</span></> : "—"}</td>
                    <td>{signal.risk_reward_ratio ?? "—"}</td>
                    <td>{signal.quality_score ?? "—"}</td>
                    <td><span className={`signal-status ${signal.status.toLowerCase()}`}>{signal.status}</span></td>
                    <td className="signal-reason">{signal.rejection_reason ?? signal.explanation ?? ""}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
