"use client";

import { type FormEvent, useEffect, useState } from "react";
import { SearchableSelect } from "@/components/SearchableSelect";
import { useInstrumentSelection } from "@/services/instrumentSelection";

type Market = { symbol: string; base_symbol?: string; description?: string };
type AccountStatus = {
  connected: boolean;
  broker: string;
  account?: { equity?: string | null } | null;
};
type RiskPolicy = {
  max_risk_per_trade_percent: string;
  max_daily_loss_percent: string;
  max_weekly_loss_percent: string;
  max_simultaneous_positions: number;
  max_aggregate_open_risk_percent: string;
  martingale_allowed: boolean;
  grid_allowed: boolean;
  live_trading_enabled: boolean;
};

type Calculation = {
  symbol: string;
  account_equity: string;
  risk_percent: string;
  risk_budget: string;
  volume: string;
  estimated_risk: string;
  risk_within_budget: boolean;
  reason: string | null;
  simulated: boolean;
};

export function RiskCalculator() {
  const [markets, setMarkets] = useState<Market[]>([]);
  const [connected, setConnected] = useState(false);
  const [broker, setBroker] = useState("");
  const [equity, setEquity] = useState<string | null>(null);
  const { symbol, setSymbol } = useInstrumentSelection();
  const [entry, setEntry] = useState("");
  const [stopLoss, setStopLoss] = useState("");
  const [riskPercent, setRiskPercent] = useState("1");
  const [calculation, setCalculation] = useState<Calculation | null>(null);
  const [policy, setPolicy] = useState<RiskPolicy | null>(null);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      try {
        const [statusResponse, marketsResponse, policyResponse] = await Promise.all([
          fetch("/api/v1/accounts/status"),
          fetch("/api/v1/markets"),
          fetch("/api/v1/risk/policy"),
        ]);
        if (!statusResponse.ok || !marketsResponse.ok || !policyResponse.ok) throw new Error("Unable to load account, market and risk data");
        const status = await statusResponse.json() as AccountStatus;
        const marketData = await marketsResponse.json() as Market[];
        const policyData = await policyResponse.json() as RiskPolicy;
        setConnected(status.connected);
        setBroker(status.broker);
        setEquity(status.account?.equity ?? null);
        setMarkets(marketData);
        setPolicy(policyData);
      } catch (cause) {
        setError(cause instanceof Error ? cause.message : "Unable to load risk calculator");
      } finally {
        setBusy(false);
      }
    }
    load();
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setCalculation(null);
    try {
      const response = await fetch("/api/v1/risk/position-size", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ symbol, entry, stop_loss: stopLoss, risk_percent: riskPercent }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail ?? "Position size could not be calculated");
      setCalculation(result as Calculation);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Position size calculation failed");
    } finally {
      setBusy(false);
    }
  }

  const canCalculate = connected && broker === "simulation";

  return (
    <div className="risk-layout">
      <section className="card panel risk-panel">
        <div className="risk-section-heading">
          <div>
            <span className="risk-eyebrow">POSITION SIZING</span>
            <h2>Calculate a position</h2>
            <p className="risk-intro">Volume is based on account equity and stop distance, capped at 1% risk and rounded down to the broker step.</p>
          </div>
        </div>
        <div className={`risk-account ${connected ? "is-connected" : "is-disconnected"}`}>
          <div className="risk-account-main">
            <span>ACCOUNT EQUITY</span>
            <strong>{equity ? `$${equity}` : "Unavailable"}</strong>
          </div>
          <span className="risk-account-status">
            <i className={`status-dot ${connected ? "live" : ""}`} aria-hidden="true" />
            {connected ? broker === "simulation" ? "Simulation connected" : "MT5 connected" : "Connect an account in Settings"}
          </span>
        </div>
        <form className="risk-form" onSubmit={submit}>
          <label className="risk-field-wide">
            <span>Instrument</span>
            <SearchableSelect
              value={symbol}
              onChange={setSymbol}
              options={markets.map((market) => ({ value: market.base_symbol ?? market.symbol, label: market.description ? `${market.base_symbol ?? market.symbol} · ${market.description}` : market.base_symbol ?? market.symbol }))}
              searchPlaceholder="Search instruments..."
              ariaLabel="Instrument"
              disabled={!markets.length}
            />
          </label>
          <div className="risk-price-grid">
            <label>
              <span>Entry price</span>
              <input required type="number" step="any" min="0" value={entry} onChange={(event) => setEntry(event.target.value)} placeholder="e.g. 1.08500" />
            </label>
            <label>
              <span>Protective stop</span>
              <input required type="number" step="any" min="0" value={stopLoss} onChange={(event) => setStopLoss(event.target.value)} placeholder="e.g. 1.08300" />
            </label>
          </div>
          <label className="risk-field-wide">
            <span>Risk per trade <small>Maximum 1%</small></span>
            <input required type="number" step="0.1" min="0.1" max="1" value={riskPercent} onChange={(event) => setRiskPercent(event.target.value)} />
          </label>
          <button className="primary-button risk-submit" type="submit" disabled={busy || !canCalculate || !markets.length}>
            {busy ? "Loading..." : "Calculate position size"}
          </button>
        </form>
        {connected && broker !== "simulation" && <p className="risk-capability-note">Position sizing is currently available only for simulation accounts. MT5 sizing is not supported by this calculator yet.</p>}
        {error && <p className="error-text" role="alert">{error}</p>}
      </section>

      <section className="card panel risk-result" aria-live="polite">
        <div className="risk-section-heading">
          <div>
            <span className="risk-eyebrow">ESTIMATE</span>
            <h2>Position size</h2>
          </div>
          {calculation && <span className={`risk-result-badge ${calculation.risk_within_budget ? "within-limit" : "over-limit"}`}>{calculation.risk_within_budget ? "Within limit" : "Over limit"}</span>}
        </div>
        {!calculation ? (
          <div className="risk-placeholder">
            <span className="risk-placeholder-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
                <path d="M5 17 10 12l3 3 6-7" />
                <path d="M14 8h5v5" />
              </svg>
            </span>
            <strong>Your sizing estimate will appear here</strong>
            <span>Enter an entry price and protective stop to calculate volume.</span>
          </div>
        ) : (
          <>
            <div className="risk-volume">{calculation.volume}<span>lots</span></div>
            <p className="risk-estimate-source">{calculation.simulated ? "Simulation estimate" : "Broker specification estimate"} · No order has been placed</p>
            <dl className="risk-breakdown">
              <div><dt>Instrument</dt><dd>{calculation.symbol}</dd></div>
              <div><dt>Account equity</dt><dd>${calculation.account_equity}</dd></div>
              <div><dt>Risk limit</dt><dd>{calculation.risk_percent}% · ${calculation.risk_budget}</dd></div>
              <div><dt>Estimated risk</dt><dd>${calculation.estimated_risk}</dd></div>
              <div><dt>Risk within limit</dt><dd className={calculation.risk_within_budget ? "risk-value-positive" : "risk-value-negative"}>{calculation.risk_within_budget ? "Yes" : "No"}</dd></div>
            </dl>
            {calculation.reason && <p className="risk-warning">{calculation.reason}</p>}
            <p className="safety-note">Sizing estimate only. No order has been placed. Values use the connected account&apos;s supported symbol specifications.</p>
          </>
        )}
      </section>
      {policy && (
        <section className="card panel risk-policy">
          <div className="risk-section-heading">
            <div>
              <span className="risk-eyebrow">ACCOUNT GUARDRAILS</span>
              <h2>Configured risk policy</h2>
              <p>Limits currently supplied by the platform configuration.</p>
            </div>
            <span className={`risk-result-badge ${policy.live_trading_enabled ? "live-enabled" : "within-limit"}`}>
              Live trading {policy.live_trading_enabled ? "enabled" : "disabled"}
            </span>
          </div>
          <div className="risk-policy-grid">
            <div><span>Risk per trade</span><strong>Max {policy.max_risk_per_trade_percent}%</strong></div>
            <div><span>Daily loss</span><strong>{policy.max_daily_loss_percent}%</strong></div>
            <div><span>Weekly loss</span><strong>{policy.max_weekly_loss_percent}%</strong></div>
            <div><span>Open positions</span><strong>Max {policy.max_simultaneous_positions}</strong></div>
            <div><span>Aggregate open risk</span><strong>{policy.max_aggregate_open_risk_percent}%</strong></div>
            <div><span>Martingale</span><strong className={policy.martingale_allowed ? "policy-allowed" : "policy-blocked"}>{policy.martingale_allowed ? "Allowed" : "Blocked"}</strong></div>
            <div><span>Grid trading</span><strong className={policy.grid_allowed ? "policy-allowed" : "policy-blocked"}>{policy.grid_allowed ? "Allowed" : "Blocked"}</strong></div>
          </div>
          <p className="safety-note">Policy values are environment-configured. This page does not change or enforce live trading permission.</p>
        </section>
      )}
    </div>
  );
}
