"use client";

import { type FormEvent, useState } from "react";

type StrategySignal = {
  strategy: string;
  direction: "BUY" | "SELL";
  entry: number;
  stop_loss: number;
  take_profit_1: number;
  take_profit_2: number;
  take_profit_3: number;
  quality_score: number;
  explanation: string;
};

type Analysis = {
  symbol: string;
  timeframe: string;
  completed_candles: number;
  trend: string;
  structure: string;
  regime: string;
  indicators: Record<string, number>;
  support_resistance: { support: number[]; resistance: number[] };
  multi_timeframe: {
    consensus: string;
    timeframes: Record<string, { structure: string; direction: string }>;
  };
  strategy_signals: StrategySignal[];
  simulated: boolean;
  data_source: "simulation" | "mt5";
  missing_timeframes?: string[];
  status?: string;
};

const symbols = ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "USDCAD", "AUDUSD", "NZDUSD", "XAUUSD"];
const timeframes = ["M5", "M15", "M30", "H1", "H4", "D1"];
const indicatorLabels: Record<string, string> = {
  ema20: "EMA 20",
  ema50: "EMA 50",
  ema200: "EMA 200",
  rsi14: "RSI 14",
  macd: "MACD",
  macd_signal: "MACD signal",
  atr14: "ATR 14",
  bollinger_upper: "Bollinger upper",
  bollinger_lower: "Bollinger lower",
  adx: "ADX",
  stochastic_k: "Stochastic %K",
};

function formatIndicator(name: string, value: number) {
  if (name.startsWith("ema") || name.startsWith("bollinger")) return value.toFixed(name === "ema200" ? 5 : 5);
  if (name === "atr14" || name === "macd" || name === "macd_signal") return value.toPrecision(5);
  return value.toFixed(2);
}

export function TechnicalAnalysis() {
  const [symbol, setSymbol] = useState("EURUSD");
  const [timeframe, setTimeframe] = useState("H1");
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function runAnalysis(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setAnalysis(null);
    try {
      const params = new URLSearchParams({ timeframe });
      const response = await fetch(`/api/v1/analysis/${encodeURIComponent(symbol)}?${params}`, { cache: "no-store" });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail ?? "Analysis request failed");
      setAnalysis(result as Analysis);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Analysis unavailable");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="analysis-content">
      <div className="signal-warning" role="note">
        <strong>
          {analysis
            ? analysis.data_source === "mt5" ? "MT5 broker candles · read only" : "Simulation candle data"
            : "Analysis data source"}
        </strong>
        <span>
          {!analysis
            ? "When MT5 is selected, analysis requires candle history from the Windows worker; otherwise generated simulation candles are used."
            : analysis.data_source === "mt5"
              ? "Analysis is based on candle history reported by the Windows MT5 worker. Signals are informational; no orders are placed."
              : "This analysis uses real external market OHLC; the account and execution remain simulated."}
        </span>
      </div>
      <section className="card panel analysis-controls">
        <div>
          <h2>Technical analysis</h2>
          <p>Indicators and strategy candidates from completed candles only.</p>
        </div>
        <form className="signal-form" onSubmit={runAnalysis}>
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
            {busy ? "Analyzing..." : "Run analysis"}
          </button>
        </form>
        {error && <p className="error-text" role="alert">{error}</p>}
      </section>

      {!analysis ? (
        <div className="card empty analysis-empty">Choose an instrument and timeframe to run analysis.</div>
      ) : analysis.status === "insufficient_completed_candles" ? (
        <div className="card empty analysis-empty">Not enough completed candles to analyze this market.</div>
      ) : (
        <>
          <section className="grid metrics analysis-summary">
            <div className="card metric"><div className="metric-label">Trend</div><div className={`metric-value analysis-label ${analysis.trend}`}>{analysis.trend.replaceAll("_", " ")}</div></div>
            <div className="card metric"><div className="metric-label">Market structure</div><div className="metric-value analysis-label">{analysis.structure.replaceAll("_", " ")}</div></div>
            <div className="card metric"><div className="metric-label">Regime</div><div className="metric-value analysis-label">{analysis.regime.replaceAll("_", " ")}</div></div>
            <div className="card metric"><div className="metric-label">Completed candles</div><div className="metric-value">{analysis.completed_candles}</div></div>
          </section>
          <section className="grid two-col">
            <div className="card panel analysis-panel">
              <h2>{analysis.symbol} · {analysis.timeframe} indicators</h2>
              <dl className="analysis-indicators">
                {Object.entries(analysis.indicators).map(([name, value]) => (
                  <div key={name}><dt>{indicatorLabels[name] ?? name}</dt><dd>{formatIndicator(name, value)}</dd></div>
                ))}
              </dl>
            </div>
            <div className="card panel analysis-panel">
              <h2>Support and resistance</h2>
              <h3>Support</h3>
              <div className="analysis-levels">{analysis.support_resistance.support.length ? analysis.support_resistance.support.map((level) => <span className="pill" key={level}>{level}</span>) : <span className="analysis-muted">No levels found</span>}</div>
              <h3>Resistance</h3>
              <div className="analysis-levels">{analysis.support_resistance.resistance.length ? analysis.support_resistance.resistance.map((level) => <span className="pill" key={level}>{level}</span>) : <span className="analysis-muted">No levels found</span>}</div>
            </div>
          </section>
          <section className="card panel analysis-panel">
            <div className="analysis-mtf-heading">
              <div>
                <h2>Multi-timeframe consensus</h2>
                <p>Weighted trend alignment across available intervals.</p>
                {analysis.missing_timeframes?.length ? (
                    <p className="analysis-muted">MT5 history not yet available: {analysis.missing_timeframes.join(", ")}</p>
                ) : null}
              </div>
              <span className={`analysis-consensus ${analysis.multi_timeframe.consensus}`}>{analysis.multi_timeframe.consensus}</span>
            </div>
            <div className="analysis-timeframes">
              {Object.entries(analysis.multi_timeframe.timeframes).map(([interval, context]) => (
                <article className="analysis-timeframe" key={interval}>
                  <strong>{interval}</strong>
                  <span className={`analysis-label ${context.direction}`}>{context.direction}</span>
                  <span>{context.structure.replaceAll("_", " ")}</span>
                </article>
              ))}
            </div>
          </section>
          <section className="card signal-list analysis-strategies">
            <div className="signal-list-heading"><div><h2>Strategy candidates</h2><p>Unexecuted analysis output · {analysis.simulated ? "simulated" : "broker data"}</p></div></div>
            {analysis.strategy_signals.length ? (
              <div className="analysis-candidate-list">
                {analysis.strategy_signals.map((candidate) => (
                  <article className="analysis-candidate" key={candidate.strategy}>
                    <div className="analysis-candidate-heading">
                      <div><strong>{candidate.strategy.replaceAll("_", " ")}</strong><span className={`signal-direction ${candidate.direction === "BUY" ? "buy-direction" : "sell-direction"}`}>{candidate.direction}</span></div>
                      <span className="pill">Quality {candidate.quality_score}/100</span>
                    </div>
                    <p>{candidate.explanation}</p>
                    <div className="analysis-level-grid">
                      <span>Entry<strong>{candidate.entry}</strong></span>
                      <span>Stop<strong>{candidate.stop_loss}</strong></span>
                      <span>TP1<strong>{candidate.take_profit_1}</strong></span>
                      <span>TP2<strong>{candidate.take_profit_2}</strong></span>
                      <span>TP3<strong>{candidate.take_profit_3}</strong></span>
                    </div>
                  </article>
                ))}
              </div>
            ) : <div className="empty analysis-empty">No strategy candidates for this selection.</div>}
          </section>
        </>
      )}
      <p className="safety-note analysis-disclaimer">Reconciled trading performance analytics are unavailable until trade history is persisted and reconciled.</p>
    </div>
  );
}
