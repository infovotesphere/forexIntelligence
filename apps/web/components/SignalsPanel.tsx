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
  simulated?: boolean;
  data_source?: "simulation" | "mt5";
};

const symbols = ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "USDCAD", "AUDUSD", "NZDUSD", "XAUUSD"];
const timeframes = ["M5", "M15", "M30", "H1", "H4", "D1"];

function formatRiskReward(value?: string): string {
  if (!value) return "—";
  const ratio = Number(value);
  return Number.isFinite(ratio) ? `${ratio.toFixed(2)}:1` : "—";
}

function signalKey(signal: Signal): string {
  return signal.signal_id ?? `${signal.symbol}-${signal.timeframe}-${signal.strategy}-${signal.created_at}`;
}

export function SignalsPanel() {
  const [signals, setSignals] = useState<Signal[]>([]);
  const [symbol, setSymbol] = useState("EURUSD");
  const [timeframe, setTimeframe] = useState("ALL");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [generationMessage, setGenerationMessage] = useState("");
  const [realtime, setRealtime] = useState<{ enabled: boolean; connected: boolean; interval_seconds: number; last_scan_at: string | null; last_scan_error: string | null; history_count: number } | null>(null);
  const [historyOnly, setHistoryOnly] = useState(false);

  useEffect(() => {
    let active = true;
    async function loadSignals() {
      try {
        const response = await fetch("/api/v1/signals", { cache: "no-store" });
        if (!response.ok) throw new Error("Unable to load trading signals");
        const result = await response.json() as { items: Signal[] };
        const realtimeResponse = await fetch("/api/v1/signals/realtime/status", { cache: "no-store" });
        if (realtimeResponse.ok) setRealtime(await realtimeResponse.json());
        if (active) {
          setSignals(result.items.filter((signal) => signal.status !== "REJECTED"));
          setError("");
        }
      } catch (cause) {
        if (active) setError(cause instanceof Error ? cause.message : "Signal service unavailable");
      } finally {
        if (active) setLoading(false);
      }
    }

    void loadSignals();
    const timer = window.setInterval(loadSignals, 15000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, []);

  async function generate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setGenerationMessage("");
    try {
      const params = new URLSearchParams({ symbol, timeframe });
      const response = await fetch(`/api/v1/signals/generate?${params}`, { method: "POST" });
      const result = await response.json() as {
        items?: unknown;
        detail?: string;
        scanned_timeframes?: unknown;
        unavailable_timeframes?: unknown;
        rejected_candidates?: unknown;
      };
      if (!response.ok) throw new Error(result.detail ?? "Signal generation failed");
      if (
        !Array.isArray(result.items)
        || !Array.isArray(result.scanned_timeframes)
        || !Array.isArray(result.unavailable_timeframes)
        || typeof result.rejected_candidates !== "number"
      ) {
        throw new Error("Signal service returned an invalid result");
      }
      const generated = result.items as Signal[];
      if (generated.some((signal) => signal.status !== "VALIDATED")) {
        throw new Error("Signal service returned a non-validated setup");
      }
      const scannedTimeframes = result.scanned_timeframes as string[];
      const unavailableTimeframes = result.unavailable_timeframes as string[];
      const rejectedCandidates = result.rejected_candidates;
      setSignals((current) => {
        const nextByKey = new Map<string, Signal>();
        for (const signal of [...current.filter((item) => item.status !== "REJECTED"), ...generated]) {
          nextByKey.set(signalKey(signal), signal);
        }
        return [...nextByKey.values()].slice(-100);
      });
      const scope = scannedTimeframes.join(", ");
      const rejectionNote = rejectedCandidates > 0
        ? ` ${rejectedCandidates} candidate${rejectedCandidates === 1 ? "" : "s"} did not pass validation.`
        : "";
      const unavailableNote = unavailableTimeframes.length > 0
        ? ` MT5 history was unavailable for ${unavailableTimeframes.join(", ")}; those timeframes were skipped without simulation fallback.`
        : "";
      setGenerationMessage(generated.length === 0
        ? `Scan complete: 0 validated setups for ${symbol} across ${scope}.${rejectionNote}${unavailableNote}`
        : `Scan complete: found ${generated.length} validated signal${generated.length === 1 ? "" : "s"} for ${symbol} across ${scope}.${rejectionNote}${unavailableNote}`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Signal generation failed");
    } finally {
      setBusy(false);
    }
  }

  const validatedCount = signals.filter((signal) => signal.status === "VALIDATED").length;
  const expiredCount = signals.filter((signal) => signal.status === "EXPIRED").length;
  const hasMt5Signals = signals.some((signal) => signal.data_source === "mt5" || signal.simulated === false);
  const hasSimulationSignals = signals.some((signal) => signal.data_source === "simulation" || signal.simulated !== false);
  const displayedSignals = historyOnly
    ? signals
    : signals.filter((signal) => signal.status === "VALIDATED");
  const sourceLabel = signals.length === 0
    ? "No signal history"
    : hasMt5Signals && hasSimulationSignals
      ? "Mixed data sources"
      : hasMt5Signals
        ? "MT5 candle history"
        : "In-memory · simulation";

  return (
    <div className="signals-content">
      <div className="signal-warning" role="note">
        <strong>{realtime?.connected ? "Realtime scanning active" : "Realtime scanning waiting for a broker"}</strong>
        <span>
          {realtime?.connected
            ? `Automatic broker-aware scan every ${realtime.interval_seconds} seconds${realtime.last_scan_at ? ` · last scan ${new Date(realtime.last_scan_at).toLocaleTimeString()}` : ""}.`
            : "Connect a simulation or MT5 account to start automatic signal scanning. Signals never place orders."}
          {realtime?.last_scan_error ? ` Last scan issue: ${realtime.last_scan_error}` : ""}
        </span>
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
              <option value="ALL">All timeframes</option>
              {timeframes.map((item) => <option key={item} value={item}>{item}</option>)}
            </select>
          </label>
          <button className="primary-button" type="submit" disabled={busy}>
            {busy ? "Scanning..." : timeframe === "ALL" ? "Scan all timeframes" : `Scan ${timeframe}`}
          </button>
        </form>
        {error && <p className="error-text" role="alert">{error}</p>}
        {generationMessage && <p className="signal-scan-result" role="status">{generationMessage}</p>}
      </section>

      <section className="signal-kpis" aria-label="Signal overview">
        <article className="card signal-kpi">
          <span>Active setups</span>
          <strong>{validatedCount}</strong>
          <small>Validated and unexpired</small>
        </article>
        <article className="card signal-kpi">
          <span>History</span>
          <strong>{realtime?.history_count ?? signals.length}</strong>
          <small>Validated signals retained in this session</small>
        </article>
        <article className="card signal-kpi">
          <span>Expired</span>
          <strong>{expiredCount}</strong>
          <small>Past the four-hour validity window</small>
        </article>
        <article className="card signal-kpi">
          <span>Scan scope</span>
          <strong>{timeframe === "ALL" ? "6 frames" : timeframe}</strong>
          <small>{timeframe === "ALL" ? "M5 through D1" : "Selected interval"}</small>
        </article>
      </section>

      <section className="card signal-list">
        <div className="signal-list-heading">
          <div><h2>{historyOnly ? "Signal history" : "Recent active signals"}</h2><p>{validatedCount} active · {expiredCount} expired</p></div>
          <div className="button-row">
            <button type="button" className={historyOnly ? "secondary-button" : "primary-button"} onClick={() => setHistoryOnly(false)}>Active</button>
            <button type="button" className={historyOnly ? "primary-button" : "secondary-button"} onClick={() => setHistoryOnly(true)}>History</button>
            <span className="pill">{sourceLabel}</span>
          </div>
        </div>
        {loading && signals.length === 0 ? (
          <div className="empty signal-empty">Loading signals...</div>
        ) : displayedSignals.length === 0 ? (
          <div className="empty signal-empty">{historyOnly ? "No signal history recorded yet." : "No active validated signals."}</div>
        ) : (
          <div className="signal-table-wrap">
            <table className="table signal-table">
              <thead>
                <tr><th>Market</th><th>Direction</th><th>Entry / stop</th><th>Targets</th><th>R:R · TP3</th><th>Quality</th><th>Status</th><th>Details</th></tr>
              </thead>
              <tbody>
                {displayedSignals.map((signal, index) => (
                  <tr key={signal.signal_id ?? `${signal.symbol}-${signal.created_at}-${index}`}>
                    <td><strong>{signal.symbol}</strong><span className="signal-meta">{signal.strategy} · {signal.timeframe} · {signal.data_source === "mt5" || signal.simulated === false ? "MT5" : "SIM"}</span></td>
                    <td><span className={`signal-direction ${signal.direction === "BUY" ? "buy-direction" : signal.direction === "SELL" ? "sell-direction" : ""}`}>{signal.direction ?? "—"}</span></td>
                    <td>{signal.entry ? <>{signal.entry}<span className="signal-meta">SL {signal.stop_loss}</span></> : "—"}</td>
                    <td>{signal.tp1 ? <>{signal.tp1}<span className="signal-meta">TP2 {signal.tp2} · TP3 {signal.tp3}</span></> : "—"}</td>
                    <td><span className="signal-ratio">{formatRiskReward(signal.risk_reward_ratio)}</span></td>
                    <td><span className="signal-quality">{signal.quality_score ?? "—"}</span></td>
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
