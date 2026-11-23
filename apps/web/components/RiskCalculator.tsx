"use client";

import { type FormEvent, useEffect, useState } from "react";

type Market = { symbol: string };
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
  const [equity, setEquity] = useState<string | null>(null);
  const [symbol, setSymbol] = useState("EURUSD");
  const [entry, setEntry] = useState("");
  const [stopLoss, setStopLoss] = useState("");
  const [calculation, setCalculation] = useState<Calculation | null>(null);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      try {
        const [statusResponse, marketsResponse] = await Promise.all([
          fetch("/api/v1/accounts/status"),
          fetch("/api/v1/markets"),
        ]);
        if (!statusResponse.ok || !marketsResponse.ok) throw new Error("Unable to load account and market data");
        const status = await statusResponse.json();
        const marketData = await marketsResponse.json() as Market[];
        setConnected(status.connected);
        setEquity(status.account?.equity ?? null);
        setMarkets(marketData);
        if (marketData.length) setSymbol(marketData[0].symbol);
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
        body: JSON.stringify({ symbol, entry, stop_loss: stopLoss, risk_percent: "1" }),
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

  return (
    <div className="risk-layout">
      <section className="card panel risk-panel">
        <h2>Position size calculator</h2>
        <p className="risk-intro">Size from account equity and stop distance. Risk is limited to 1% and volume is rounded down to the broker step.</p>
        <div className="risk-account">
          <span>Account equity</span>
          <strong>{equity ? `$${equity}` : "Unavailable"}</strong>
          <span className={connected ? "risk-connected" : "risk-disconnected"}>
            {connected ? "Broker connected" : "Connect an account in Settings"}
          </span>
        </div>
        <form className="risk-form" onSubmit={submit}>
          <label>
            <span>Instrument</span>
            <select required value={symbol} onChange={(event) => setSymbol(event.target.value)} disabled={!markets.length}>
              {markets.map((market) => <option key={market.symbol} value={market.symbol}>{market.symbol}</option>)}
            </select>
          </label>
          <label>
            <span>Entry price</span>
            <input required type="number" step="any" min="0" value={entry} onChange={(event) => setEntry(event.target.value)} placeholder="e.g. 1.08500" />
          </label>
          <label>
            <span>Stop-loss price</span>
            <input required type="number" step="any" min="0" value={stopLoss} onChange={(event) => setStopLoss(event.target.value)} placeholder="e.g. 1.08300" />
          </label>
          <button className="primary-button" type="submit" disabled={busy || !connected || !markets.length}>
            {busy ? "Loading..." : "Calculate safe volume"}
          </button>
        </form>
        {error && <p className="error-text" role="alert">{error}</p>}
      </section>

      <section className="card panel risk-result" aria-live="polite">
        <h2>Calculation</h2>
        {!calculation ? (
          <div className="risk-placeholder">Enter an entry and protective stop to estimate position size.</div>
        ) : (
          <>
            <div className="risk-volume">{calculation.volume}<span>lots</span></div>
            <dl className="risk-breakdown">
              <div><dt>Instrument</dt><dd>{calculation.symbol}</dd></div>
              <div><dt>Account equity</dt><dd>${calculation.account_equity}</dd></div>
              <div><dt>Risk limit</dt><dd>{calculation.risk_percent}% · ${calculation.risk_budget}</dd></div>
              <div><dt>Estimated risk</dt><dd>${calculation.estimated_risk}</dd></div>
              <div><dt>Risk within limit</dt><dd>{calculation.risk_within_budget ? "Yes" : "No"}</dd></div>
            </dl>
            {calculation.reason && <p className="risk-warning">{calculation.reason}</p>}
            <p className="safety-note">Sizing estimate only. No order has been placed. Values use the connected account&apos;s supported symbol specifications.</p>
          </>
        )}
      </section>
    </div>
  );
}
