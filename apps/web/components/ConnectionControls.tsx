"use client";

import { useEffect, useState } from "react";
import { getApiBaseUrl } from "@/services/api";

type Status = {
  connected: boolean;
  environment: string;
  broker: string;
  account_id?: string;
  engine_running: boolean;
  live_trading_enabled: boolean;
  simulated: boolean;
  message: string;
  account?: { currency: string; balance: string | null; equity: string | null } | null;
};

export function ConnectionControls({ compact = false }: { compact?: boolean }) {
  const [status, setStatus] = useState<Status | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function refresh() {
    try {
      const response = await fetch(`${getApiBaseUrl()}/api/v1/accounts/status`);
      if (!response.ok) throw new Error("Unable to reach the backend");
      const account = await response.json();
      const engineResponse = await fetch(`${getApiBaseUrl()}/api/v1/engine/status`);
      if (!engineResponse.ok) throw new Error("Unable to read engine status");
      const engine = await engineResponse.json();
      setStatus({
        connected: account.connected,
        environment: account.environment,
        broker: account.environment === "simulation" ? "simulation" : account.broker,
        account_id: account.account_id,
        engine_running: engine.running,
        live_trading_enabled: engine.live_trading_enabled,
        simulated: account.simulated,
        message: engine.message,
        account: account.account,
      });
      setError("");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Connection failed");
    }
  }

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void refresh();
    }, 0);
    return () => window.clearTimeout(timer);
  }, []);

  async function connectSimulation() {
    setBusy(true);
    try {
      const response = await fetch(`${getApiBaseUrl()}/api/v1/accounts/connect`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ broker: "simulation" }),
      });
      if (!response.ok) throw new Error("Simulation connection failed");
      await refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Connection failed");
    } finally {
      setBusy(false);
    }
  }

  async function toggleEngine() {
    setBusy(true);
    try {
      const action = status?.engine_running ? "stop" : "start";
      const response = await fetch(`${getApiBaseUrl()}/api/v1/engine/${action}`, { method: "POST" });
      if (!response.ok) throw new Error("Unable to update engine state");
      await refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Engine action failed");
    } finally {
      setBusy(false);
    }
  }

  if (compact) {
    return (
      <button className="status status-button" onClick={status?.connected ? toggleEngine : connectSimulation} disabled={busy} title={status?.message}>
        <span className={`status-dot ${status?.connected ? "live" : ""}`} />
        {status?.connected ? (status.engine_running ? "Engine running" : "Engine stopped") : "Connect demo"}
      </button>
    );
  }

  return (
    <section className="card panel">
      <h2>Broker connection</h2>
      <div className="connection-summary">
        <span className={`status-dot ${status?.connected ? "live" : ""}`} />
        <div>
          <strong>
            {status?.connected
              ? status.broker === "mt5"
                ? status.environment === "live" ? "MT5 live account connected · read-only" : "MT5 demo account connected"
                : "Simulation demo connected"
              : status?.broker === "mt5" ? "Waiting for Windows MT5 worker" : "Disconnected"}
          </strong>
          <p>{status?.message ?? "Checking broker status..."}</p>
          {status?.connected && status.account?.balance && (
            <p>{status.account.currency} {status.account.balance} balance · {status.account.currency} {status.account.equity} equity</p>
          )}
        </div>
      </div>
      {error && <p className="error-text">{error}</p>}
      <div className="button-row">
        <button className="primary-button" onClick={connectSimulation} disabled={busy}>
          Connect simulation demo
        </button>
        <button
          className="secondary-button"
          onClick={toggleEngine}
          disabled={busy || !status?.connected || status?.environment === "live"}
        >
          {status?.engine_running ? "Stop engine" : status?.environment === "live" ? "Read-only account" : "Start engine"}
        </button>
      </div>
      {status?.connected && status.broker === "simulation" && (
        <p className="safety-note">Simulation mode only. No real broker credentials or live execution are used.</p>
      )}
      {status?.connected && status.broker === "mt5" && (
        <p className="safety-note">Connected to MT5 {status.environment}. This integration is read-only; all trading execution remains simulated.</p>
      )}
    </section>
  );
}
