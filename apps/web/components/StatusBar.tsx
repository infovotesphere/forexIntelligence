"use client";

import { useEffect, useState } from "react";
import { getApiBaseUrl } from "@/services/api";

export function StatusBar() {
  const [status, setStatus] = useState({ connected: false, broker: "none", environment: "demo", engine: false, message: "Checking..." });

  async function refresh() {
    try {
      const [accountResponse, engineResponse] = await Promise.all([
        fetch(`${getApiBaseUrl()}/api/v1/accounts/status`, { cache: "no-store" }),
        fetch(`${getApiBaseUrl()}/api/v1/engine/status`, { cache: "no-store" }),
      ]);
      if (!accountResponse.ok || !engineResponse.ok) throw new Error("API unavailable");
      const account = await accountResponse.json();
      const engine = await engineResponse.json();
      setStatus({
        connected: Boolean(account.connected),
        broker: account.broker,
        environment: account.broker === "simulation"
          ? "Simulation demo"
          : account.broker === "mt5"
            ? account.environment === "live" ? "MT5 live · read only" : "MT5 demo"
            : "Demo account",
        engine: Boolean(engine.running),
        message: engine.message,
      });
    } catch {
      setStatus({ connected: false, broker: "none", environment: "Demo account", engine: false, message: "API unavailable" });
    }
  }

  useEffect(() => {
    const initialRefresh = window.setTimeout(() => {
      void refresh();
    }, 0);
    const interval = window.setInterval(() => {
      void refresh();
    }, 5000);
    return () => {
      window.clearTimeout(initialRefresh);
      window.clearInterval(interval);
    };
  }, []);

  return (
    <div className="status-group">
      <div className="status" title={status.message}>
        <span className={`status-dot ${status.connected ? "live" : ""}`} /> {status.environment}
      </div>
      <div className="status" title={status.message}>
        <span className={`status-dot ${status.engine ? "live" : ""}`} /> {status.engine ? "Engine running" : "Engine stopped"}
      </div>
      <div className="status" title={status.message}>
        <span className={`status-dot ${status.broker === "mt5" && status.connected ? "live" : ""}`} />
        MT5 {status.broker === "mt5" && status.connected ? "connected" : status.broker === "mt5" ? "waiting for worker" : "disconnected"}
      </div>
    </div>
  );
}
