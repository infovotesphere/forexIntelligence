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
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  async function refresh() {
    setLoading(true);
    setError("");
    setSuccess("");
    try {
      const response = await fetch("/api/v1/notifications/status", { cache: "no-store" });
      if (!response.ok) throw new Error("Unable to read notification status");
      setStatus(await response.json() as NotificationStatus);
    } catch (cause) {
      setStatus(null);
      setError(cause instanceof Error ? cause.message : "Notification status unavailable");
    } finally {
      setLoading(false);
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
    <div className="notification-layout">
      <section className="card panel notification-card">
        <div className="notification-heading">
          <div>
            <span className="notification-eyebrow">DELIVERY CHANNEL</span>
            <h2>Telegram notifications</h2>
            <p>Verify the server-side connection and send a test message.</p>
          </div>
          <span className={`notification-state ${loading ? "is-checking" : status?.configured ? "is-configured" : status ? "needs-setup" : "is-unavailable"}`}>
            {loading ? "Checking" : status?.configured ? "Configured" : status ? "Setup required" : "Unavailable"}
          </span>
        </div>
        <div className="notification-connection" aria-live="polite">
          <span className={`notification-icon ${status?.configured ? "is-configured" : ""}`} aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
              <path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9" />
              <path d="M10 21h4" />
            </svg>
          </span>
          <div>
            <strong>
              {loading ? "Checking delivery status" : status?.configured ? `${status.provider} is ready` : status ? "Telegram is not configured" : "Connection status unavailable"}
            </strong>
            <p>
              {loading
                ? "Reading configuration from the API."
                : status?.configured
                  ? `Destination chat ID: ${status.chat_id}`
                  : status
                    ? "Add the bot token and destination chat ID to the API environment."
                    : "Check the API connection, then retry the status check."}
            </p>
          </div>
        </div>
        <div className="notification-facts">
          <div><span>Provider</span><strong>{status?.provider ?? "Telegram"}</strong></div>
          <div><span>Credentials</span><strong>Stored on the API</strong></div>
          <div><span>Browser access</span><strong>Token never exposed</strong></div>
        </div>
        {error && <p className="error-text notification-feedback" role="alert">{error}</p>}
        {success && <p className="success-text notification-feedback" role="status">{success}</p>}
        <div className="notification-actions">
          <button className="primary-button" type="button" onClick={sendTest} disabled={busy || loading || !status?.configured}>
            {busy ? "Sending test..." : "Send test notification"}
          </button>
          <button className="secondary-button" type="button" onClick={refresh} disabled={loading}>
            {loading ? "Checking..." : "Refresh status"}
          </button>
        </div>
        <p className="safety-note">Sending a test delivers a real Telegram message. No notification is sent until you select the test button.</p>
      </section>

      <aside className="card panel notification-guide">
        <span className="notification-eyebrow">SETUP GUIDE</span>
        <h2>Connect a delivery destination</h2>
        <p className="notification-guide-copy">Configuration is managed by the API service, not in this browser.</p>
        <ol className="notification-steps">
          <li><span>01</span><div><strong>Add the API variables</strong><p><code>TELEGRAM_BOT_TOKEN</code> and <code>TELEGRAM_CHAT_ID</code></p></div></li>
          <li><span>02</span><div><strong>Restart or redeploy the API</strong><p>The service reads these values from its environment.</p></div></li>
          <li><span>03</span><div><strong>Refresh and verify</strong><p>Use the test button to confirm Telegram delivery.</p></div></li>
        </ol>
        <div className="notification-security">
          <strong>Credential safety</strong>
          <p>The bot token is never returned to the web app. Keep it private and rotate it if it is exposed.</p>
        </div>
      </aside>
    </div>
  );
}
