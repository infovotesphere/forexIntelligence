"use client";

import { type FormEvent, useState } from "react";

type ConnectionResult = { message?: string; detail?: string; connected?: boolean; broker?: string };
type MT5Environment = "demo" | "live";

export function MT5ConnectionForm() {
  const [accountId, setAccountId] = useState("");
  const [password, setPassword] = useState("");
  const [server, setServer] = useState("");
  const [environment, setEnvironment] = useState<MT5Environment>("demo");
  const [liveReadOnlyConfirmed, setLiveReadOnlyConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    setError("");
    try {
      const response = await fetch("/api/v1/accounts/connect", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          broker: "mt5",
          environment,
          live_read_only_confirmed: liveReadOnlyConfirmed,
          account_id: accountId,
          password,
          server,
        }),
      });
      const result = await response.json() as ConnectionResult;
      if (!response.ok) throw new Error(result.detail ?? result.message ?? "Could not queue MT5 connection");
      setMessage(result.message ?? "MT5 connection request submitted");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "MT5 connection failed");
    } finally {
      setPassword("");
      setBusy(false);
    }
  }

  return (
    <section className="card panel mt5-form">
      <div className="mt5-form-heading">
        <div>
          <h2>MetaTrader 5 connection</h2>
          <p>Connect an MT5 account for broker-sourced account and market data.</p>
        </div>
        <span className="pill">Paper trading only</span>
      </div>
      <div className="account-mode" role="group" aria-label="MT5 account environment">
        <button
          type="button"
          className={environment === "demo" ? "account-mode-option selected" : "account-mode-option"}
          aria-pressed={environment === "demo"}
          onClick={() => { setEnvironment("demo"); setLiveReadOnlyConfirmed(false); }}
        >
          <strong>Demo account</strong><span>Recommended for testing</span>
        </button>
        <button
          type="button"
          className={environment === "live" ? "account-mode-option selected live-option" : "account-mode-option"}
          aria-pressed={environment === "live"}
          onClick={() => setEnvironment("live")}
        >
          <strong>Live account</strong><span>Read-only connection</span>
        </button>
      </div>
      {environment === "live" ? (
        <div className="live-warning" role="note">
          <strong>Live account — read-only</strong>
          <span>This connects to a real-money account for monitoring only. No MT5 orders or position changes are allowed, and live trading remains disabled.</span>
          <label className="confirmation">
            <input
              type="checkbox"
              checked={liveReadOnlyConfirmed}
              onChange={(event) => setLiveReadOnlyConfirmed(event.target.checked)}
            />
            I understand this is a live account and confirm read-only monitoring with paper trading only.
          </label>
        </div>
      ) : (
        <p className="mode-note">Demo credentials are verified against the MT5 demo account type. All orders remain simulated.</p>
      )}
      <form onSubmit={submit}>
        <label>
          <span>Account number</span>
          <input required inputMode="numeric" autoComplete="username" value={accountId} onChange={(event) => setAccountId(event.target.value)} placeholder="Numeric MT5 login" />
        </label>
        <label>
          <span>MT5 password</span>
          <input required type="password" autoComplete="new-password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="Password for this account" />
        </label>
        <label>
          <span>Broker server</span>
          <input required autoComplete="off" placeholder="Exact server name shown in MT5" value={server} onChange={(event) => setServer(event.target.value)} />
        </label>
        {message && <p className="success-text" role="status">{message}</p>}
        {error && <p className="error-text" role="alert">{error}</p>}
        <button className="primary-button" type="submit" disabled={busy || (environment === "live" && !liveReadOnlyConfirmed)}>
          {busy ? "Submitting securely..." : environment === "live" ? "Connect live account (read-only)" : "Connect demo account"}
        </button>
      </form>
      <p className="safety-note">Credentials are encrypted by the API and handed once to the authenticated Windows worker. The password is not saved in the browser or returned by the API.</p>
    </section>
  );
}
