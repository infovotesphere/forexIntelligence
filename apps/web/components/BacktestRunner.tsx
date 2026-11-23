"use client";

import { type FormEvent, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { CandlestickReplay, type ReplayCandle, type ReplayMarker } from "@/components/CandlestickReplay";
import { BacktestEquityCurve, type BacktestEquityPoint } from "@/components/BacktestEquityCurve";

type BacktestTrade = {
  signal_time: string;
  exit_time: string | null;
  direction: "BUY" | "SELL";
  entry: string;
  stop_loss: string;
  take_profit: string;
  exit_price: string | null;
  outcome: "STOP_LOSS" | "TAKE_PROFIT" | "OPEN";
  r_multiple: string | null;
  candles_held: number;
  ambiguous_exit: boolean;
};

type BacktestResult = {
  symbol: string;
  timeframe: string;
  strategy: string;
  bars_tested: number;
  simulated: boolean;
  data_source: "simulation" | "mt5";
  candles: ReplayCandle[];
  equity_curve: BacktestEquityPoint[];
  execution_model: string;
  summary: {
    total_trades: number;
    resolved_trades: number;
    wins: number;
    losses: number;
    open_trades: number;
    rejected_candidates: number;
    win_rate_percent: string | null;
    net_r: string;
    average_r: string | null;
    profit_factor: string | null;
    max_drawdown_r: string;
  };
  trades: BacktestTrade[];
};

const symbols = ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "USDCAD", "AUDUSD", "NZDUSD", "XAUUSD"];
const timeframes = ["M5", "M15", "M30", "H1", "H4", "D1"];
const strategies = [
  { value: "trend_following", label: "Trend following" },
  { value: "breakout_retest", label: "Breakout / retest" },
];
const initialReplayBars = 100;

function formatR(value: string | null): string {
  if (value === null) return "—";
  const parsed = Number(value);
  return Number.isFinite(parsed) ? `${parsed.toFixed(2)}R` : "—";
}

function formatMultiple(value: string | null): string {
  if (value === null) return "—";
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed.toFixed(2) : "—";
}

export function BacktestRunner() {
  const searchParams = useSearchParams();
  const [symbol, setSymbol] = useState("EURUSD");
  const [timeframe, setTimeframe] = useState("H1");
  const [bars, setBars] = useState(500);
  const [strategy, setStrategy] = useState(() => {
    const requestedStrategy = searchParams.get("strategy");
    return strategies.find((item) => item.value === requestedStrategy)?.value ?? "trend_following";
  });
  const [result, setResult] = useState<BacktestResult | null>(null);
  const [visibleCount, setVisibleCount] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [speed, setSpeed] = useState(2);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const replayComplete = result !== null && visibleCount >= result.candles.length;

  const replayMarkers = useMemo<ReplayMarker[]>(() => {
    if (!result) return [];
    return result.trades.flatMap((trade) => {
      const markers: ReplayMarker[] = [{
        time: trade.signal_time,
        direction: trade.direction,
        kind: "entry",
        label: trade.direction,
      }];
      if (trade.exit_time) {
        markers.push({
          time: trade.exit_time,
          direction: trade.direction,
          kind: "exit",
          label: trade.outcome === "TAKE_PROFIT" ? "TP" : "SL",
        });
      }
      return markers;
    });
  }, [result]);

  useEffect(() => {
    if (!isPlaying || !result || replayComplete) return;
    const timer = window.setTimeout(
      () => setVisibleCount((current) => Math.min(current + 1, result.candles.length)),
      1000 / speed,
    );
    return () => window.clearTimeout(timer);
  }, [isPlaying, replayComplete, result, speed, visibleCount]);

  async function run(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setIsPlaying(false);
    setError("");
    setResult(null);
    setVisibleCount(0);
    try {
      const response = await fetch("/api/v1/backtesting/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ symbol, timeframe, strategy, bars }),
      });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail ?? "Backtest could not be completed");
      const backtest = body as BacktestResult;
      if (!Array.isArray(backtest.candles) || backtest.candles.length < 2) {
        throw new Error("Backtest returned insufficient candle history");
      }
      setResult(backtest);
      setVisibleCount(Math.min(initialReplayBars, backtest.candles.length - 1));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Backtest failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="backtest-content">
      <div className="signal-warning" role="note">
        <strong>Historical candle replay · paper only</strong>
        <span>Simulation mode uses real external market OHLC for replay and analysis; the account and execution remain simulated. MT5 accounts use read-only broker candles and will not substitute external or simulated data if the feed is missing or stale. No broker orders are sent.</span>
      </div>
      <section className="card panel backtest-controls">
        <div><h2>Configure replay</h2><p>Choose the market, timeframe, strategy, and history length.</p></div>
        <form className="signal-form" onSubmit={run}>
          <label><span>Instrument</span><select value={symbol} onChange={(event) => setSymbol(event.target.value)}>{symbols.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
          <label><span>Timeframe</span><select value={timeframe} onChange={(event) => setTimeframe(event.target.value)}>{timeframes.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
          <label><span>Strategy</span><select value={strategy} onChange={(event) => setStrategy(event.target.value)}>{strategies.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label>
          <label><span>History bars</span><select value={bars} onChange={(event) => setBars(Number(event.target.value))}>{[100, 260, 500].map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
          <button className="primary-button" type="submit" disabled={busy}>{busy ? "Loading candles..." : "Load backtest"}</button>
        </form>
        {error && <p className="error-text" role="alert">{error}</p>}
      </section>

      {result && (
        <>
          <div className="backtest-result-heading">
            <div><h2>{result.symbol} · {result.timeframe}</h2><p>{strategies.find((item) => item.value === result.strategy)?.label ?? result.strategy} · {result.bars_tested} completed candles</p></div>
            <span className={`pill ${result.simulated ? "simulation-pill" : "broker-pill"}`}>{result.simulated ? "REAL MARKET OHLC · SIM ACCOUNT" : "MT5 · BROKER CANDLES"}</span>
          </div>
          <section className="card replay-controls">
            <div className="replay-transport">
              <button type="button" className="secondary-button" disabled={visibleCount <= 1} onClick={() => { setIsPlaying(false); setVisibleCount((current) => Math.max(1, current - 1)); }}>Step back</button>
              <button
                type="button"
                className="primary-button"
                onClick={() => {
                  if (replayComplete && result) {
                    setVisibleCount(Math.min(initialReplayBars, result.candles.length - 1));
                    setIsPlaying(true);
                  } else {
                    setIsPlaying((playing) => !playing);
                  }
                }}
              >
                {replayComplete ? "Replay from start" : isPlaying ? "Pause" : "Play"}
              </button>
              <button type="button" className="secondary-button" disabled={visibleCount >= result.candles.length} onClick={() => { setIsPlaying(false); setVisibleCount((current) => Math.min(result.candles.length, current + 1)); }}>Step forward</button>
              <label className="replay-speed"><span>Speed</span><select value={speed} onChange={(event) => setSpeed(Number(event.target.value))}>{[1, 2, 5, 10, 20].map((item) => <option key={item} value={item}>{item}×</option>)}</select></label>
            </div>
            <input
              className="replay-slider"
              type="range"
              min={1}
              max={result.candles.length}
              value={visibleCount}
              aria-label="Replay candle position"
              onChange={(event) => { setIsPlaying(false); setVisibleCount(Number(event.target.value)); }}
            />
            <div className="replay-progress"><span>{visibleCount} / {result.candles.length} candles</span><span>{replayComplete ? "Replay complete" : "Future candles hidden"}</span></div>
          </section>
          <CandlestickReplay candles={result.candles} markers={replayMarkers} visibleCount={visibleCount} />
          {replayComplete ? (
            <>
              <section className="grid metrics backtest-metrics">
                <div className="card metric"><div className="metric-label">Closed trades</div><div className="metric-value">{result.summary.resolved_trades}</div></div>
                <div className="card metric"><div className="metric-label">Win rate</div><div className="metric-value">{result.summary.win_rate_percent === null ? "—" : `${Number(result.summary.win_rate_percent).toFixed(1)}%`}</div></div>
                <div className="card metric"><div className="metric-label">Net result</div><div className={`metric-value ${Number(result.summary.net_r) >= 0 ? "position-profit" : "position-loss"}`}>{formatR(result.summary.net_r)}</div></div>
                <div className="card metric"><div className="metric-label">Average R / trade</div><div className="metric-value">{formatR(result.summary.average_r)}</div></div>
                <div className="card metric"><div className="metric-label">Max drawdown</div><div className="metric-value">{formatR(result.summary.max_drawdown_r)}</div></div>
                <div className="card metric"><div className="metric-label">Profit factor</div><div className="metric-value">{formatMultiple(result.summary.profit_factor)}</div></div>
                <div className="card metric"><div className="metric-label">Open at end</div><div className="metric-value">{result.summary.open_trades}</div></div>
              </section>
              <BacktestEquityCurve points={result.equity_curve} />
              <section className="card backtest-trades">
                <div className="signal-list-heading"><div><h2>Replay trades</h2><p>{result.summary.wins} wins · {result.summary.losses} losses · {result.summary.rejected_candidates} rejected candidates</p></div></div>
                {!result.trades.length ? <div className="empty backtest-empty">No validated strategy trades in this replay window.</div> : (
                  <div className="backtest-table-wrap">
                    <table className="table backtest-table">
                      <thead><tr><th>Signal time</th><th>Side</th><th>Entry</th><th>Stop</th><th>TP3</th><th>Outcome</th><th>R</th><th>Bars</th><th>Assumption</th></tr></thead>
                      <tbody>{result.trades.map((trade, index) => (
                        <tr key={`${trade.signal_time}-${index}`}>
                          <td>{new Date(trade.signal_time).toLocaleString()}</td>
                          <td>{trade.direction}</td>
                          <td>{trade.entry}</td>
                          <td>{trade.stop_loss}</td>
                          <td>{trade.take_profit}</td>
                          <td><span className={`signal-status ${trade.outcome === "TAKE_PROFIT" ? "validated" : trade.outcome === "STOP_LOSS" ? "rejected" : "expired"}`}>{trade.outcome.replaceAll("_", " ")}</span></td>
                          <td>{formatR(trade.r_multiple)}</td>
                          <td>{trade.candles_held}</td>
                          <td>{trade.ambiguous_exit ? "Stop-first: both levels touched" : "—"}</td>
                        </tr>
                      ))}</tbody>
                    </table>
                  </div>
                )}
              </section>
            </>
          ) : (
            <section className="card replay-pending">
              <strong>Replay in progress</strong>
              <span>Full-run performance is hidden until the remaining candles have played.</span>
            </section>
          )}
          <p className="safety-note backtest-model">{result.execution_model}</p>
        </>
      )}
    </div>
  );
}
