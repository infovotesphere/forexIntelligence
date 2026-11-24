"use client";

import { useEffect, useState } from "react";
import { startVisiblePolling } from "@/services/polling";

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
  const [lastChecked, setLastChecked] = useState<Date | null>(null);

  useEffect(() => {
    let active = true;

    async function refresh() {
      try {
        const response = await fetch("/api/v1/health", { cache: "no-store" });
        if (!response.ok) throw new Error("Unable to load system health");
        const result = await response.json() as HealthStatus;
        if (active) {
          setHealth(result);
          setLastChecked(new Date());
          setError("");
        }
      } catch (cause) {
        if (active) setError(cause instanceof Error ? cause.message : "System health unavailable");
      }
    }

    void refresh();
    const stopPolling = startVisiblePolling(refresh, 10000);
    return () => {
      active = false;
      stopPolling();
    };
  }, []);

  const checks = health ? [
    { label: "API", value: health.status === "ok" ? "Healthy" : "Degraded", state: health.status === "ok" ? "healthy" : "warning", detail: "Application services and endpoints" },
    { label: "Database", value: health.database === "healthy" ? "Healthy" : "Unavailable", state: health.database === "healthy" ? "healthy" : "warning", detail: "Persistent account and trade data" },
    { label: "Redis", value: health.redis === "healthy" ? "Healthy" : "Unavailable", state: health.redis === "healthy" ? "healthy" : "warning", detail: "Cache and background task service" },
    { label: "Broker", value: health.broker === "connected" ? "Connected" : "Disconnected", state: health.broker === "connected" ? "healthy" : "idle", detail: health.broker_type === "mt5" ? "Broker connection via MT5" : "Broker account connection" },
    { label: "MT5 worker", value: health.mt5_worker === "connected" ? "Connected" : "Not connected", state: health.mt5_worker === "connected" ? "healthy" : "idle", detail: "Windows terminal bridge" },
    { label: "Trading engine", value: health.engine_running ? "Running" : "Stopped", state: health.engine_running ? "healthy" : "idle", detail: "Automated signal and execution service" },
  ] : [];

  return (
    <section className="card system-health-card">
      <header className="system-health-header">
        <div className="system-health-title">
          <span className="system-health-icon" aria-hidden="true">
            <svg viewBox="0 0 24 24"><path d="M4 13h4l2.5-7 4 12 2.5-5h3" /><path d="M3 4v16h18" /></svg>
          </span>
          <div>
            <span className="system-eyebrow">Platform</span>
            <h2>System health</h2>
            <p>Services, broker connectivity, and execution status</p>
          </div>
        </div>
        <span className={`system-overall-status ${health?.status ?? "loading"}`}>
          <i />
          {health ? health.status === "ok" ? "All systems operational" : "Degraded service" : "Checking services"}
        </span>
      </header>

      {error && <p className="error-text" role="alert">{error}</p>}
      {checks.length > 0 ? (
        <div className="system-health-grid" aria-label="System health checks">
          {checks.map((check) => (
            <article className={`system-check ${check.state}`} key={check.label}>
              <div className="system-check-heading">
                <span className="system-check-indicator"><i /></span>
                <span>{check.label}</span>
              </div>
              <strong>{check.value}</strong>
              <p>{check.detail}</p>
            </article>
          ))}
        </div>
      ) : (
        <div className="system-health-loading" role="status">
          {error ? "System health checks are unavailable." : "Loading health checks…"}
        </div>
      )}

      {health && (
        <div className="system-health-details">
          <div><span>Environment</span><strong>{health.environment}</strong></div>
          <div><span>Broker type</span><strong>{health.broker_type}</strong></div>
          <div className={health.live_trading ? "live-enabled" : "live-disabled"}>
            <span>Live trading</span>
            <strong>{health.live_trading ? "Enabled" : "Disabled"}</strong>
          </div>
        </div>
      )}

      <footer className="system-health-footer">
        <span>Read-only operational status · auto-refreshes every 10 seconds</span>
        {lastChecked && <span>Last checked {lastChecked.toLocaleTimeString()}</span>}
      </footer>
    </section>
  );
}
