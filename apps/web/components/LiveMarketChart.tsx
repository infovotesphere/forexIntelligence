"use client";

import { useEffect, useState } from "react";
import {
  CandlestickReplay,
  type PositionOverlay,
  type ReplayCandle,
  type ReplayMarker,
} from "@/components/CandlestickReplay";
import { SearchableSelect } from "@/components/SearchableSelect";
import { startVisiblePolling } from "@/services/polling";

const timeframes = ["M1", "M5", "M15", "M30", "H1", "H4", "D1"] as const;
const noMarkers: ReplayMarker[] = [];

type Props = {
  symbol: string;
  symbols: string[];
  positions: PositionOverlay[];
  onSymbolChange: (symbol: string) => void;
};

type CandleResponse = {
  symbol: string;
  timeframe: string;
  data_source: "mt5" | "real_market" | "simulation";
  simulated: boolean;
  candles: ReplayCandle[];
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isDataSource(value: unknown): value is CandleResponse["data_source"] {
  return value === "mt5" || value === "real_market" || value === "simulation";
}

function responseError(value: unknown): string {
  if (!isRecord(value)) return "Unable to load market candles";
  const detail = value.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const messages = detail.flatMap((item) => isRecord(item) && typeof item.msg === "string" ? [item.msg] : []);
    if (messages.length) return messages.join("; ");
  }
  return "Unable to load market candles";
}

function parseCandleResponse(value: unknown): CandleResponse | null {
  if (!isRecord(value) || !Array.isArray(value.candles)) return null;
  if (
    typeof value.symbol !== "string"
    || typeof value.timeframe !== "string"
    || !isDataSource(value.data_source)
    || typeof value.simulated !== "boolean"
  ) return null;

  const candles: ReplayCandle[] = [];
  for (const item of value.candles) {
    if (
      !isRecord(item)
      || typeof item.time !== "string"
      || typeof item.open !== "string"
      || typeof item.high !== "string"
      || typeof item.low !== "string"
      || typeof item.close !== "string"
      || typeof item.volume !== "string"
    ) return null;
    candles.push({
      time: item.time,
      open: item.open,
      high: item.high,
      low: item.low,
      close: item.close,
      volume: item.volume,
    });
  }

  return {
    symbol: value.symbol,
    timeframe: value.timeframe,
    data_source: value.data_source,
    simulated: value.simulated,
    candles,
  };
}

function sourceLabel(source: CandleResponse["data_source"]): string {
  if (source === "mt5") return "MT5 · BROKER CANDLES";
  if (source === "real_market") return "REAL MARKET OHLC · PAPER EXECUTION";
  return "SIMULATED MARKET PREVIEW";
}

export function LiveMarketChart({ symbol, symbols, positions, onSymbolChange }: Props) {
  const [timeframe, setTimeframe] = useState<(typeof timeframes)[number]>("M5");
  const [result, setResult] = useState<CandleResponse | null>(null);
  const [requestState, setRequestState] = useState({ key: "", loading: true, error: "", updatedAt: "" });
  const requestKey = `${symbol}:${timeframe}`;

  useEffect(() => {
    let active = true;
    let hasLoaded = false;
    let lastUpdatedAt = "";

    async function refresh() {
      if (!hasLoaded && active) setRequestState({ key: requestKey, loading: true, error: "", updatedAt: "" });
      try {
        const query = new URLSearchParams({ timeframe, limit: "300" });
        const response = await fetch(`/api/v1/markets/${encodeURIComponent(symbol)}/candles?${query}`, { cache: "no-store" });
        const body: unknown = await response.json().catch(() => null);
        if (!response.ok) throw new Error(responseError(body));
        const result = parseCandleResponse(body);
        if (!result) {
          throw new Error("The market candle service returned an invalid response");
        }
        if (active) {
          setResult(result);
          lastUpdatedAt = new Date().toLocaleTimeString();
          setRequestState({ key: requestKey, loading: false, error: "", updatedAt: lastUpdatedAt });
          hasLoaded = true;
        }
      } catch (cause) {
        if (active) {
          setRequestState({
            key: requestKey,
            loading: false,
            error: cause instanceof Error ? cause.message : "Market candle feed unavailable",
            updatedAt: lastUpdatedAt,
          });
        }
      }
    }

    const stopPolling = startVisiblePolling(refresh, 15000);
    return () => {
      active = false;
      stopPolling();
    };
  }, [requestKey, symbol, timeframe]);

  const currentResult = result?.symbol === symbol && result.timeframe === timeframe ? result : null;
  const currentRequest = requestState.key === requestKey ? requestState : { key: requestKey, loading: true, error: "", updatedAt: "" };
  const candles = currentResult?.candles ?? [];

  return (
    <div className="live-market-workspace">
      <section className="card live-market-toolbar">
        <div className="live-market-title">
          <span className="live-market-icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
              <path d="M4 19V9m5 10V5m6 14v-7m5 7V3" />
              <path d="M2 19h20" />
            </svg>
          </span>
          <div>
            <strong>Market chart</strong>
            <p>{currentResult
              ? `${sourceLabel(currentResult.data_source)}${currentRequest.updatedAt ? ` · updated ${currentRequest.updatedAt}` : ""}`
              : "Loading candle feed…"}</p>
          </div>
        </div>
        <div className="live-market-controls">
          <label>
            <span>Instrument</span>
            <SearchableSelect
              value={symbol}
              onChange={onSymbolChange}
              options={symbols.map((item) => ({ value: item, label: item }))}
              ariaLabel="Chart instrument"
              searchPlaceholder="Search instruments..."
            />
          </label>
          <div className="live-timeframe-picker" role="group" aria-label="Chart timeframe">
            {timeframes.map((item) => (
              <button
                key={item}
                type="button"
                className={timeframe === item ? "selected" : ""}
                aria-pressed={timeframe === item}
                onClick={() => setTimeframe(item)}
              >
                {item}
              </button>
            ))}
          </div>
        </div>
      </section>
      {currentRequest.error && <p className="error-text live-market-error" role="alert">{currentRequest.error}</p>}
      {currentRequest.loading && candles.length === 0 ? (
        <section className="card live-market-loading">Loading {symbol} {timeframe} candles…</section>
      ) : candles.length ? (
        <>
          {positions.length > 0 && (
            <section className="live-position-strip" aria-label={`${positions.length} open position${positions.length === 1 ? "" : "s"} on ${symbol}`}>
              <div className="live-position-strip-heading"><strong>Open on chart</strong><span>{positions.length} active</span></div>
              <div className="live-position-strip-list">
                {positions.map((position) => (
                  <article className="live-position-chip" key={`${position.source ?? "POSITION"}-${position.ticket}`}>
                    <span className={`signal-direction ${position.direction === "BUY" ? "buy-direction" : "sell-direction"}`}>
                      {position.source === "BROKER" ? "MT5" : "PRACTICE"} {position.direction}
                    </span>
                    <strong>{position.volume} {position.symbol ?? symbol}</strong>
                    <span>Entry <b>{position.price_open}</b></span>
                    <span>Current <b>{position.price_current}</b></span>
                    {Number(position.stop_loss) > 0 && <span>SL <b>{position.stop_loss}</b></span>}
                    {Number(position.take_profit) > 0 && <span>TP <b>{position.take_profit}</b></span>}
                  </article>
                ))}
              </div>
            </section>
          )}
          <CandlestickReplay
            candles={candles}
            markers={noMarkers}
            visibleCount={candles.length}
            live
            positions={positions}
            timeframeOptions={timeframes}
            activeTimeframe={timeframe}
            onTimeframeChange={(value) => {
              const nextTimeframe = timeframes.find((item) => item === value);
              if (nextTimeframe) setTimeframe(nextTimeframe);
            }}
          />
        </>
      ) : (
        <section className="card live-market-loading live-market-empty">Candles are unavailable for this instrument and timeframe.</section>
      )}
    </div>
  );
}
