"use client";

import { type FormEvent, useState } from "react";

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

export function BacktestRunner() {
  const [symbol, setSymbol] = useState("EURUSD");
  const [timeframe, setTimeframe] = useState("H1");
  const [strategy, setStrategy] = useState("trend_following");
  const [result, setResult] = useState<BacktestResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function run(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setResult(null);
    try {
      const response = await fetch("/api/v1/backtesting/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ symbol, timeframe, strategy, bars: 260 }),
      });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail ?? "Backtest could not be completed");
      setResult(body as BacktestResult);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Backtest failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="backtest-content">
      <div className="signal-warning" role="note">
        <strong>Simulation backtest only</strong>
        <span>Generated development candles are not historical broker prices. No trades are placed. Results exclude spread, slippage, commissions, partial exits and portfolio-level risk limits.</span>
      </div>
      <section className="card panel backtest-controls">
        <div><h2>Configure replay</h2><p>Tests the selected strategy over up to 260 simulated candles.</p></div>
        <form className="signal-form" onSubmit={run}>
          <label><span>Instrument</span><select value={symbol} onChange={(event) => setSymbol(event.target.value)}>{symbols.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
          <label><span>Timeframe</span><select value={timeframe} onChange={(event) => setTimeframe(event.target.value)}>{timeframes.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
          <label><span>Strategy</span><select value={strategy} onChange={(event) => setStrategy(event.target.value)}>{strategies.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label>
          <button className="primary-button" type="submit" disabled={busy}>{busy ? "Running replay..." : "Run backtest"}</button>
        </form>
        {error && <p className="error-text" role="alert">{error}</p>}
      </section>

      {result && (
        <>
          <div className="backtest-result-heading">
            <div><h2>{result.symbol} · {result.timeframe}</h2><p>{strategies.find((item) => item.value === result.strategy)?.label ?? result.strategy} · {result.bars_tested} completed candles</p></div>
            <span className="pill simulation-pill">SIMULATED</span>
          </div>
          <section className="grid metrics backtest-metrics">
            <div className="card metric"><div className="metric-label">Closed trades</div><div className="metric-value">{result.summary.resolved_trades}</div></div>
            <div className="card metric"><div className="metric-label">Win rate</div><div className="metric-value">{result.summary.win_rate_percent === null ? "—" : `${Number(result.summary.win_rate_percent).toFixed(1)}%`}</div></div>
            <div className="card metric"><div className="metric-label">Net result</div><div className={`metric-value ${Number(result.summary.net_r) >= 0 ? "position-profit" : "position-loss"}`}>{result.summary.net_r}R</div></div>
            <div className="card metric"><div className="metric-label">Max drawdown</div><div className="metric-value">{result.summary.max_drawdown_r}R</div></div>
            <div className="card metric"><div className="metric-label">Profit factor</div><div className="metric-value">{result.summary.profit_factor ?? "—"}</div></div>
            <div className="card metric"><div className="metric-label">Open at end</div><div className="metric-value">{result.summary.open_trades}</div></div>
          </section>
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
                      <td>{trade.r_multiple ?? "—"}</td>
                      <td>{trade.candles_held}</td>
                      <td>{trade.ambiguous_exit ? "Stop-first: both levels touched" : "—"}</td>
                    </tr>
                  ))}</tbody>
                </table>
              </div>
            )}
          </section>
          <p className="safety-note backtest-model">{result.execution_model}</p>
        </>
      )}
    </div>
  );
}
