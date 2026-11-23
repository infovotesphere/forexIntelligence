"use client";

import { useEffect, useState } from "react";

type HealthStatus = {
  status: "ok" | "degraded";
  database: "healthy" | "unhealthy";
  redis: "healthy" | "unhealthy";
  broker: "connected" | "disconnected";
  broker_type: string;
  mt5_worker: "connected" | "not_connected";
  engine_running: boolean;
  live_trading: boolean;
  environment: string;
};

export function SystemStatus() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;

    async function refresh() {
      try {
        const response = await fetch("/api/v1/health", { cache: "no-store" });
        if (!response.ok) throw new Error("Unable to load system health");
        const result = await response.json() as HealthStatus;
        if (active) {
          setHealth(result);
          setError("");
        }
      } catch (cause) {
        if (active) setError(cause instanceof Error ? cause.message : "System health unavailable");
      }
    }

    void refresh();
    const timer = window.setInterval(() => { void refresh(); }, 10000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, []);

  const rows = health ? [
    ["API", health.status === "ok" ? "Healthy" : "Degraded"],
    ["Database", health.database === "healthy" ? "Healthy" : "Unavailable"],
    ["Redis", health.redis === "healthy" ? "Healthy" : "Unavailable"],
    ["Broker", health.broker === "connected" ? "Connected" : "Disconnected"],
    ["MT5 worker", health.mt5_worker === "connected" ? "Connected" : "Not connected"],
    ["Trading engine", health.engine_running ? "Running" : "Stopped"],
  ] : [];

  return (
    <section className="card panel">
      <div className="positions-toolbar">
        <div>
          <strong>{health ? `System ${health.status}` : "Checking system health"}</strong>
          <p>Runtime status · refreshing every 10 seconds</p>
        </div>
        <span className={`pill ${health?.live_trading ? "broker-pill" : "simulation-pill"}`}>
          {health?.live_trading ? "LIVE TRADING ENABLED" : "LIVE TRADING DISABLED"}
        </span>
      </div>
      {error && <p className="error-text" role="alert">{error}</p>}
      {rows.length > 0 ? (
        <dl className="risk-breakdown">
          {rows.map(([label, value]) => (
            <div key={label}><dt>{label}</dt><dd>{value}</dd></div>
          ))}
          <div><dt>Environment</dt><dd>{health?.environment}</dd></div>
          <div><dt>Broker type</dt><dd>{health?.broker_type}</dd></div>
        </dl>
      ) : (
        <div className="empty history-empty">Loading runtime status.</div>
      )}
      <p className="safety-note">Read-only operational status. Live trading remains disabled unless explicitly configured outside this dashboard.</p>
    </section>
  );
}
