import Link from "next/link";

const strategies = [
  {
    name: "Trend following",
    key: "trend_following",
    status: "Signal generation",
    description: "Looks for aligned medium- and long-term trend, momentum confirmation, and supportive market structure.",
    rules: [
      "Requires at least 200 completed candles.",
      "BUY: EMA 50 above EMA 200, RSI at least 52, MACD above its signal, and bullish structure.",
      "SELL: EMA 50 below EMA 200, RSI at most 48, MACD below its signal, and bearish structure.",
    ],
    risk: "Stop at 1.5 ATR; targets at 1.5, 3.0 and 4.5 ATR.",
  },
  {
    name: "Breakout / retest",
    key: "breakout_retest",
    status: "Signal generation",
    description: "Checks for a close beyond a recent range followed by a retest near the broken boundary.",
    rules: [
      "Requires at least 30 completed candles.",
      "Uses the prior 27-candle range and inspects the latest three candles for breakout and retest.",
      "Rejects candidates that do not satisfy the shared protective-stop and reward/risk validator.",
    ],
    risk: "Stop at 1.5 ATR; targets at 1.5, 3.0 and 4.5 ATR.",
  },
];

export function StrategyCatalogue() {
  return (
    <div className="strategy-content">
      <div className="signal-warning" role="note">
        <strong>Strategies generate analysis only</strong>
        <span>Neither strategy submits, modifies, or closes broker orders. Signal and backtest data currently use generated simulation candles.</span>
      </div>
      <section className="strategy-grid">
        {strategies.map((strategy) => (
          <article className="card strategy-card" key={strategy.key}>
            <div className="strategy-heading">
              <div><h2>{strategy.name}</h2><p>{strategy.description}</p></div>
              <span className="pill">{strategy.status}</span>
            </div>
            <h3>Entry checks</h3>
            <ul>{strategy.rules.map((rule) => <li key={rule}>{rule}</li>)}</ul>
            <div className="strategy-risk"><span>Risk model</span><strong>{strategy.risk}</strong></div>
            <div className="strategy-footer">
              <Link href="/signals">Generate candidates</Link>
              <Link href="/backtesting">Open backtesting</Link>
            </div>
          </article>
        ))}
      </section>
      <section className="card strategy-validation">
        <h2>Shared signal validation</h2>
        <div className="strategy-validation-grid">
          <div><strong>Protective stop required</strong><span>BUY stops must be below entry; SELL stops must be above entry.</span></div>
          <div><strong>Minimum reward/risk</strong><span>TP3 must offer at least 2:1 reward to risk after tick-size rounding.</span></div>
          <div><strong>Signal expiry</strong><span>Validated signals expire after four hours.</span></div>
          <div><strong>Execution</strong><span>Live broker order execution is disabled; candidates are not orders.</span></div>
        </div>
      </section>
    </div>
  );
}
