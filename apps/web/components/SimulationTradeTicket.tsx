"use client";

import { type FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { SearchableSelect } from "@/components/SearchableSelect";
import { useInstrumentSelection } from "@/services/instrumentSelection";
import { usePracticeVolume } from "@/services/practiceTradePreferences";

type Market = {
  symbol: string;
  bid: string;
  ask: string;
  tick_size: string;
  tick_value: string;
  minimum_volume: string;
  volume_step: string;
  digits: number;
};

type PracticeAccount = {
  currency: string;
  balance: string;
  equity: string;
};

type OrderType = "MARKET" | "BUY_STOP" | "SELL_STOP";
type IconName = "plus" | "market" | "buy" | "sell" | "close";

type Props = {
  onSubmitted?: (symbol?: string) => void;
  initialSymbol?: string;
  triggerLabel?: string;
  triggerDescription?: string;
  selectedEntryPrice?: string | null;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function formatApiError(value: unknown, fallback: string): string {
  if (!isRecord(value)) return fallback;
  const detail = value.detail;
  const errors = Array.isArray(detail) ? detail : [detail];
  const messages = errors.flatMap((item) => {
    if (typeof item === "string") return [item];
    if (!isRecord(item)) return [];
    const message = typeof item.msg === "string"
      ? item.msg
      : typeof item.message === "string"
        ? item.message
        : "";
    if (!message) return [];
    const location = Array.isArray(item.loc)
      ? item.loc.filter((part): part is string | number => typeof part === "string" || typeof part === "number").slice(1)
      : [];
    return [`${location.length ? `${location.join(".")}: ` : ""}${message}`];
  });
  return messages.join("; ") || fallback;
}

function TradeIcon({ name }: { name: IconName }) {
  const paths: Record<IconName, React.ReactNode> = {
    plus: <><path d="M12 5v14" /><path d="M5 12h14" /></>,
    market: <><path d="M4 7h15m0 0-3-3m3 3-3 3" /><path d="M20 17H5m0 0 3 3m-3-3 3-3" /></>,
    buy: <><path d="M12 19V5" /><path d="m6 11 6-6 6 6" /></>,
    sell: <><path d="M12 5v14" /><path d="m18 13-6 6-6-6" /></>,
    close: <><path d="m6 6 12 12" /><path d="M18 6 6 18" /></>,
  };
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {paths[name]}
    </svg>
  );
}

export function SimulationTradeTicket({
  onSubmitted,
  initialSymbol = "EURUSD",
  triggerLabel = "Place a trade",
  triggerDescription,
  selectedEntryPrice,
}: Props) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [markets, setMarkets] = useState<Market[]>([]);
  const [account, setAccount] = useState<PracticeAccount | null>(null);
  const { symbol, setSymbol } = useInstrumentSelection(initialSymbol);
  const [orderType, setOrderType] = useState<OrderType>("MARKET");
  const [marketDirection, setMarketDirection] = useState<"BUY" | "SELL">("BUY");
  const { volume, setVolume } = usePracticeVolume();
  const [stopPriceInput, setStopPriceInput] = useState({
    selectedEntryPrice: selectedEntryPrice ?? null,
    value: selectedEntryPrice ?? "",
  });
  const selectedEntry = selectedEntryPrice ?? null;
  const stopPrice = stopPriceInput.selectedEntryPrice === selectedEntry
    ? stopPriceInput.value
    : selectedEntry ?? "";
  const [stopLoss, setStopLoss] = useState("");
  const [takeProfit, setTakeProfit] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    let active = true;
    async function loadPracticeAccount() {
      try {
        const [marketsResponse, accountResponse] = await Promise.all([
          fetch("/api/v1/practice/markets", { cache: "no-store" }),
          fetch("/api/v1/practice/status", { cache: "no-store" }),
        ]);
        if (!marketsResponse.ok || !accountResponse.ok) {
          throw new Error("Unable to load the practice account or its instruments");
        }
        const instruments = await marketsResponse.json() as Market[];
        const accountStatus = await accountResponse.json() as { account: PracticeAccount };
        if (active) {
          setMarkets(instruments);
          setAccount(accountStatus.account);
        }
      } catch (cause) {
        if (active) setError(cause instanceof Error ? cause.message : "Practice account unavailable");
      } finally {
        if (active) setLoading(false);
      }
    }
    void loadPracticeAccount();
    return () => {
      active = false;
    };
  }, []);

  const market = markets.find((item) => item.symbol === symbol);
  const direction = orderType === "BUY_STOP" ? "BUY" : orderType === "SELL_STOP" ? "SELL" : marketDirection;
  const entry = market
    ? orderType === "MARKET"
      ? Number(direction === "BUY" ? market.ask : market.bid)
      : Number(stopPrice)
    : NaN;
  const estimatedRisk = useMemo(() => {
    if (!market || !stopLoss.trim() || !Number.isFinite(entry) || !Number.isFinite(Number(stopLoss)) || !Number.isFinite(Number(volume))) {
      return null;
    }
    const ticksAtRisk = Math.abs(entry - Number(stopLoss)) / Number(market.tick_size);
    const value = ticksAtRisk * Number(market.tick_value) * Number(volume);
    return Number.isFinite(value) ? value : null;
  }, [entry, market, stopLoss, volume]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
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
          order_type: orderType,
          volume,
          stop_price: orderType === "MARKET" ? null : stopPrice,
          stop_loss: stopLoss.trim() || null,
          take_profit: takeProfit.trim() || null,
          idempotency_key: idempotencyKey,
        }),
      });
      const body: unknown = await response.json().catch(() => null);
      if (!response.ok) throw new Error(formatApiError(body, "Practice order could not be placed"));
      if (!isRecord(body)) throw new Error("The practice service returned an invalid order response");
      setSuccess(body.pending_order
        ? `${orderType.replace("_", " ")} for ${symbol} placed and waiting for its trigger.`
        : `${direction} ${volume} ${symbol} market position opened.`);
      setStopPriceInput({ selectedEntryPrice: selectedEntry, value: "" });
      setStopLoss("");
      setTakeProfit("");
      onSubmitted?.(symbol);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Practice order could not be placed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="practice-launch">
      <button
        className="card practice-launch-button"
        type="button"
        aria-haspopup="dialog"
        onClick={() => {
          setError("");
          setSuccess("");
          dialogRef.current?.showModal();
        }}
      >
        <span className="practice-launch-icon"><TradeIcon name="plus" /></span>
        <span className="practice-launch-copy">
          <strong>{triggerLabel}</strong>
          <small>{triggerDescription ?? (account
            ? `${account.currency} ${Number(account.balance).toFixed(2)} virtual balance · market and stop orders`
            : loading ? "Loading independent practice account…" : "Open the independent practice ticket")}</small>
        </span>
        <span className="practice-launch-action">Open ticket <span aria-hidden="true">→</span></span>
      </button>

      <dialog ref={dialogRef} className="practice-trade-dialog" aria-labelledby="practice-dialog-title">
        <div className="practice-modal-shell">
          <header className="practice-modal-header">
            <div>
              <span className="practice-eyebrow">SIMULATED EXECUTION</span>
              <h2 id="practice-dialog-title">Place a trade</h2>
              <p>Practice only. Nothing is sent to your broker.</p>
            </div>
            <button className="practice-modal-close" type="button" aria-label="Close trade dialog" onClick={() => dialogRef.current?.close()}>
              <TradeIcon name="close" />
            </button>
          </header>

          <div className="practice-account-metrics" aria-label="Practice account summary">
            <div><span>Virtual balance</span><strong>{account ? `${account.currency} ${Number(account.balance).toFixed(2)}` : "—"}</strong></div>
            <div><span>Equity</span><strong>{account ? `${account.currency} ${Number(account.equity).toFixed(2)}` : "—"}</strong></div>
          </div>

          <form className="practice-form" onSubmit={submit}>
            <div className="practice-type-picker" role="group" aria-label="Order type">
              <button type="button" className={orderType === "MARKET" ? "selected market" : ""} aria-pressed={orderType === "MARKET"} onClick={() => setOrderType("MARKET")}>
                <TradeIcon name="market" /><span>Market</span>
              </button>
              <button type="button" className={orderType === "BUY_STOP" ? "selected buy" : ""} aria-pressed={orderType === "BUY_STOP"} onClick={() => setOrderType("BUY_STOP")}>
                <TradeIcon name="buy" /><span>Buy stop</span>
              </button>
              <button type="button" className={orderType === "SELL_STOP" ? "selected sell" : ""} aria-pressed={orderType === "SELL_STOP"} onClick={() => setOrderType("SELL_STOP")}>
                <TradeIcon name="sell" /><span>Sell stop</span>
              </button>
            </div>
            <p className="practice-type-hint">
              {orderType === "MARKET"
                ? "Execute immediately at the current bid or ask."
                : orderType === "BUY_STOP"
                  ? "Open a buy position when price rises to your trigger."
                  : "Open a sell position when price falls to your trigger."}
            </p>

            {orderType === "MARKET" && (
              <div className="practice-side-picker" role="group" aria-label="Trade direction">
                <button type="button" className={marketDirection === "BUY" ? "selected buy" : ""} aria-pressed={marketDirection === "BUY"} onClick={() => setMarketDirection("BUY")}>
                  <TradeIcon name="buy" />
                  <span><strong>Buy / Long</strong><small>Ask · {market?.ask ?? "—"}</small></span>
                </button>
                <button type="button" className={marketDirection === "SELL" ? "selected sell" : ""} aria-pressed={marketDirection === "SELL"} onClick={() => setMarketDirection("SELL")}>
                  <TradeIcon name="sell" />
                  <span><strong>Sell / Short</strong><small>Bid · {market?.bid ?? "—"}</small></span>
                </button>
              </div>
            )}

            <section className="practice-form-section" aria-label="Trade details">
              <div className="practice-section-heading"><div><span>01</span><strong>Trade details</strong></div><small>Choose the market and size</small></div>
              <div className="practice-form-fields">
                <label><span>Instrument</span>
                  <SearchableSelect
                    value={symbol}
                    onChange={setSymbol}
                    options={markets.map((item) => ({ value: item.symbol, label: item.symbol }))}
                    searchPlaceholder="Search instruments..."
                    ariaLabel="Instrument"
                    disabled={loading || !markets.length}
                  />
                </label>
                <label><span>Volume <small>Lots</small></span>
                  <input required type="number" step={market?.volume_step ?? "any"} min={market?.minimum_volume ?? "0.001"} value={volume} onChange={(event) => setVolume(event.target.value)} />
                </label>
                {orderType !== "MARKET" && (
                  <label className="practice-entry-price"><span>Trigger price <small>Required · {orderType === "BUY_STOP" ? "above ask" : "below bid"}</small></span>
                    <input required type="number" step={market?.tick_size ?? "any"} min={market?.tick_size ?? "0.00001"} value={stopPrice} onChange={(event) => setStopPriceInput({ selectedEntryPrice: selectedEntry, value: event.target.value })} placeholder={orderType === "BUY_STOP" ? market?.ask : market?.bid} />
                  </label>
                )}
              </div>
            </section>

            <fieldset className="practice-protection">
              <legend><span className="practice-legend-number">02</span><strong>Protection levels</strong><small>Optional</small></legend>
              <p>Add a stop loss or take profit, or leave both empty.</p>
              <div className="practice-protection-fields">
                <label><span>Stop loss</span>
                  <input type="number" step={market?.tick_size ?? "any"} min={market?.tick_size ?? "0.00001"} value={stopLoss} onChange={(event) => setStopLoss(event.target.value)} placeholder="Not set" />
                </label>
                <label><span>Take profit</span>
                  <input type="number" step={market?.tick_size ?? "any"} min={market?.tick_size ?? "0.00001"} value={takeProfit} onChange={(event) => setTakeProfit(event.target.value)} placeholder="Not set" />
                </label>
              </div>
            </fieldset>

            <div className="practice-order-summary">
              <div><span>Estimated entry</span><strong>{Number.isFinite(entry) ? entry.toFixed(market?.digits ?? 5) : "—"}</strong><small>{orderType === "MARKET" ? `${direction} · ${direction === "BUY" ? "Ask" : "Bid"}` : "Order trigger"}</small></div>
              <div><span>Position size</span><strong>{volume || "—"} <small>lots</small></strong><small>{symbol}</small></div>
              <div className={estimatedRisk === null ? "risk-unprotected" : "risk-protected"}><span>Risk at stop</span><strong>{estimatedRisk === null ? "Unprotected" : `${account?.currency ?? "USD"} ${estimatedRisk.toFixed(2)}`}</strong><small>{estimatedRisk === null ? "No loss cap" : "Estimated maximum"}</small></div>
            </div>

            {error && <p className="error-text practice-feedback" role="alert">{error}</p>}
            {success && <p className="success-text practice-feedback" role="status">{success}</p>}
            <div className="practice-form-footer">
              <button className={`primary-button practice-submit ${direction === "SELL" ? "sell-submit" : ""}`} type="submit" disabled={busy || loading || !markets.length}>
                <TradeIcon name={orderType === "SELL_STOP" ? "sell" : direction === "BUY" ? "buy" : "sell"} />
                {busy ? "Placing order…" : orderType === "MARKET" ? `Place ${direction === "BUY" ? "buy" : "sell"} market trade` : `Place ${orderType.replace("_", " ").toLowerCase()}`}
              </button>
              <p className="practice-risk-note">Virtual funds only. Without a stop loss, potential losses are not capped by risk controls.</p>
            </div>
          </form>
        </div>
      </dialog>
    </section>
  );
}
