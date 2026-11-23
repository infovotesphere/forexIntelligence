"use client";

import { useEffect, useState } from "react";

type NotificationStatus = {
  configured: boolean;
  chat_id: string;
  provider: string;
};

export function NotificationSettings() {
  const [status, setStatus] = useState<NotificationStatus | null>(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [busy, setBusy] = useState(false);

  async function refresh() {
    try {
      const response = await fetch("/api/v1/notifications/status", { cache: "no-store" });
      if (!response.ok) throw new Error("Unable to read notification status");
      setStatus(await response.json() as NotificationStatus);
      setError("");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Notification status unavailable");
    }
  }

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void refresh();
    }, 0);
    return () => window.clearTimeout(timer);
  }, []);

  async function sendTest() {
    setBusy(true);
    setError("");
    setSuccess("");
    try {
      const response = await fetch("/api/v1/notifications/test", { method: "POST" });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail ?? "Test notification failed");
      setSuccess("Telegram test notification delivered.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Test notification failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="card panel">
      <h2>Telegram delivery</h2>
      <div className="connection-summary">
        <span className={`status-dot ${status?.configured ? "live" : ""}`} />
        <div>
          <strong>{status?.configured ? "Telegram configured" : "Telegram not configured"}</strong>
          <p>
            {status?.configured
              ? `Chat ID ending in ${status.chat_id.replace("…", "")}`
              : "Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in the API environment."}
          </p>
        </div>
      </div>
      {error && <p className="error-text" role="alert">{error}</p>}
      {success && <p className="success-text" role="status">{success}</p>}
      <div className="button-row">
        <button className="secondary-button" type="button" onClick={sendTest} disabled={busy || !status?.configured}>
          {busy ? "Sending…" : "Send test notification"}
        </button>
      </div>
      <p className="safety-note">The bot token is kept in the API environment and is never returned to the browser.</p>
    </section>
  );
}
