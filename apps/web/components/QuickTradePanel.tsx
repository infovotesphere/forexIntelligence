"use client";

import { useEffect, useState } from "react";
import { startVisiblePolling } from "@/services/polling";
import { usePracticeVolume } from "@/services/practiceTradePreferences";

type Props = {
  symbol: string;
  onSubmitted?: () => void;
};

type MarketQuote = {
  symbol: string;
  bid: string;
  ask: string;
  spread: string;
  digits: number;
  minimum_volume: string;
  maximum_volume: string;
  volume_step: string;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function apiError(value: unknown): string {
  if (!isRecord(value)) return "Practice order could not be placed";
  if (typeof value.detail === "string") return value.detail;
  if (Array.isArray(value.detail)) {
    const messages = value.detail.flatMap((item) => isRecord(item) && typeof item.msg === "string" ? [item.msg] : []);
    if (messages.length) return messages.join("; ");
  }
  return "Practice order could not be placed";
}

function parseMarkets(value: unknown): MarketQuote[] | null {
  if (!Array.isArray(value)) return null;
  const markets: MarketQuote[] = [];
  for (const item of value) {
    if (
      !isRecord(item)
      || typeof item.symbol !== "string"
      || typeof item.bid !== "string"
      || typeof item.ask !== "string"
      || typeof item.spread !== "string"
      || typeof item.digits !== "number"
      || typeof item.minimum_volume !== "string"
      || typeof item.maximum_volume !== "string"
      || typeof item.volume_step !== "string"
    ) return null;
    markets.push({
      symbol: item.symbol,
      bid: item.bid,
      ask: item.ask,
      spread: item.spread,
      digits: item.digits,
      minimum_volume: item.minimum_volume,
      maximum_volume: item.maximum_volume,
      volume_step: item.volume_step,
    });
  }
  return markets;
}

export function QuickTradePanel({ symbol, onSubmitted }: Props) {
  const [markets, setMarkets] = useState<MarketQuote[]>([]);
  const { volume, setVolume } = usePracticeVolume();
  const [busySide, setBusySide] = useState<"BUY" | "SELL" | null>(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [quoteTime, setQuoteTime] = useState("");

  useEffect(() => {
    let active = true;
    async function refreshQuotes() {
      try {
        const response = await fetch("/api/v1/practice/markets", { cache: "no-store" });
        const payload: unknown = await response.json().catch(() => null);
        if (!response.ok) throw new Error(apiError(payload));
        const result = parseMarkets(payload);
        if (!result) throw new Error("Practice quotes returned an invalid response");
        if (active) {
          setMarkets(result);
          setQuoteTime(new Date().toLocaleTimeString());
          setError("");
        }
      } catch (cause) {
        if (active) setError(cause instanceof Error ? cause.message : "Practice quotes are unavailable");
      }
    }

    const stopPolling = startVisiblePolling(refreshQuotes, 5000);
    return () => {
      active = false;
      stopPolling();
    };
  }, []);

  const market = markets.find((item) => item.symbol === symbol);
  const volumeNumber = Number(volume);
  const volumeStep = Number(market?.volume_step);
  const volumeSteps = volumeNumber / volumeStep;
  const validVolume = Boolean(
    market
    && Number.isFinite(volumeNumber)
    && volumeNumber >= Number(market.minimum_volume)
    && volumeNumber <= Number(market.maximum_volume)
    && Number.isFinite(volumeSteps)
    && Math.abs(volumeSteps - Math.round(volumeSteps)) < 1e-8,
  );

  async function placeMarketOrder(direction: "BUY" | "SELL") {
    if (!market || !validVolume || busySide) return;
    setBusySide(direction);
    setError("");
    setSuccess("");
    try {
      const idempotencyKey = typeof crypto.randomUUID === "function"
        ? crypto.randomUUID()
        : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
      const response = await fetch("/api/v1/practice/orders", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          symbol,
          direction,
          order_type: "MARKET",
          volume,
          stop_price: null,
          stop_loss: null,
          take_profit: null,
          idempotency_key: idempotencyKey,
        }),
      });
      const payload: unknown = await response.json().catch(() => null);
      if (!response.ok) throw new Error(apiError(payload));
      if (!isRecord(payload) || payload.accepted !== true) throw new Error("Practice order response was invalid");
      const position = isRecord(payload.position) ? payload.position : null;
      const fillPrice = position && typeof position.price_open === "string" ? position.price_open : "";
      setSuccess(`${direction} ${volume} ${symbol} filled${fillPrice ? ` at ${fillPrice}` : ""}.`);
      onSubmitted?.();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Practice order could not be placed");
    } finally {
      setBusySide(null);
    }
  }

  return (
    <section className="card quick-trade-panel">
      <div className="quick-trade-heading">
        <div>
          <span className="practice-eyebrow">PRACTICE · VIRTUAL</span>
          <h2>Instant trade</h2>
        </div>
        <span className="quick-trade-symbol">{symbol}</span>
      </div>

      <div className="quick-trade-controls">
        <label className="quick-trade-volume">
          <span>Volume <small>Lots</small></span>
          <input
            type="number"
            inputMode="decimal"
            min={market?.minimum_volume ?? "0.001"}
            max={market?.maximum_volume ?? "100"}
            step={market?.volume_step ?? "0.001"}
            value={volume}
            onChange={(event) => setVolume(event.target.value)}
            aria-label="Trade volume in lots"
          />
        </label>
        <button
          className="quick-trade-button sell"
          type="button"
          disabled={!market || !validVolume || busySide !== null || Boolean(error)}
          aria-label={`Sell ${symbol} at current bid ${market?.bid ?? ""}`}
          onClick={() => void placeMarketOrder("SELL")}
        >
          <span>{busySide === "SELL" ? "Placing…" : "SELL"}</span>
          <strong>{market ? Number(market.bid).toFixed(market.digits) : "—"}</strong>
          <small>{busySide === "SELL" ? "Sending market order" : "Market · Bid"}</small>
        </button>
        <button
          className="quick-trade-button buy"
          type="button"
          disabled={!market || !validVolume || busySide !== null || Boolean(error)}
          aria-label={`Buy ${symbol} at current ask ${market?.ask ?? ""}`}
          onClick={() => void placeMarketOrder("BUY")}
        >
          <span>{busySide === "BUY" ? "Placing…" : "BUY"}</span>
          <strong>{market ? Number(market.ask).toFixed(market.digits) : "—"}</strong>
          <small>{busySide === "BUY" ? "Sending market order" : "Market · Ask"}</small>
        </button>
      </div>

      <div className="quick-trade-footer">
        <span>{market ? `Spread ${Number(market.spread).toFixed(market.digits)}` : "Loading virtual quote…"}{quoteTime ? ` · quote ${quoteTime}` : ""}</span>
        {volume && !validVolume && <span className="quick-trade-validation">Volume must match this instrument’s limits and step.</span>}
      </div>
      {error && <p className="error-text quick-trade-feedback" role="alert">{error}</p>}
      {success && <p className="success-text quick-trade-feedback" role="status">{success}</p>}
    </section>
  );
}
