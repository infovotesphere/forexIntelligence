"use client";

import { useEffect, useMemo, useState } from "react";
import { LiveMarketChart } from "@/components/LiveMarketChart";
import { PracticePositionsManager } from "@/components/PracticePositionsManager";
import { QuickTradePanel } from "@/components/QuickTradePanel";
import { SimulationTradeTicket } from "@/components/SimulationTradeTicket";
import { instrumentGroups } from "@/services/instruments";
import { useInstrumentSelection } from "@/services/instrumentSelection";
import { startVisiblePolling } from "@/services/polling";

type Position = {
  ticket: string;
  symbol: string;
  direction: "BUY" | "SELL";
  volume: string;
  price_open: string;
  price_current: string;
  profit: string;
  stop_loss: string;
  take_profit: string;
  simulated: boolean;
};

type PositionResponse = {
  items: Position[];
  total: number;
  connected: boolean;
  broker: string;
  environment: string;
  simulated: boolean;
  trading_mode: string;
};

type MarketInstrument = {
  symbol: string;
  base_symbol?: string;
};

type PendingOrder = {
  ticket: string;
  symbol: string;
  order_type: "BUY_STOP" | "SELL_STOP";
  direction: "BUY" | "SELL";
  volume: string;
  stop_price: string;
  stop_loss: string;
  take_profit: string;
};

type PracticePositionsResponse = {
  items: Position[];
  total: number;
  pending_orders: PendingOrder[];
  pending_total: number;
  account: { currency: string; balance: string; equity: string };
};

const practiceSymbols: ReadonlySet<string> = new Set(instrumentGroups.flatMap((group) => group.symbols));

export function PositionsTable() {
  const [data, setData] = useState<PositionResponse | null>(null);
  const [markets, setMarkets] = useState<MarketInstrument[]>([]);
  const [practice, setPractice] = useState<PracticePositionsResponse | null>(null);
  const [error, setError] = useState("");
  const [practiceError, setPracticeError] = useState("");
  const { symbol: selectedSymbol, setSymbol: setSelectedSymbol, ready: selectionReady, hasSavedSelection } = useInstrumentSelection();
  const [refreshVersion, setRefreshVersion] = useState(0);

  useEffect(() => {
    let active = true;
    async function refresh() {
      try {
        const [positionResponse, marketResponse, practiceResponse] = await Promise.all([
          fetch("/api/v1/positions", { cache: "no-store" }),
          fetch("/api/v1/markets", { cache: "no-store" }),
          fetch("/api/v1/practice/positions", { cache: "no-store" }),
        ]);
        if (!positionResponse.ok || !marketResponse.ok) throw new Error("Unable to load position and market data");
        const positionResult = await positionResponse.json() as PositionResponse;
        const marketResult = await marketResponse.json() as MarketInstrument[];
        const practiceResult = practiceResponse.ok
          ? await practiceResponse.json() as PracticePositionsResponse
          : null;
        if (active) {
          setData(positionResult);
          setMarkets(marketResult);
          setPractice(practiceResult);
          setPracticeError(practiceResponse.ok ? "" : "The independent practice account is temporarily unavailable.");
          setError("");
        }
      } catch (cause) {
        if (active) setError(cause instanceof Error ? cause.message : "Position feed unavailable");
      }
    }

    const stopPolling = startVisiblePolling(refresh, 5000);
    return () => {
      active = false;
      stopPolling();
    };
  }, [refreshVersion]);

  const positions = useMemo(() => data?.items ?? [], [data]);
  const chartSymbols = useMemo(() => {
    const symbols = new Set<string>();
    for (const market of markets) symbols.add((market.base_symbol ?? market.symbol).toUpperCase());
    for (const position of positions) {
      const quote = markets.find((market) => market.symbol.toUpperCase() === position.symbol.toUpperCase());
      symbols.add((quote?.base_symbol ?? position.symbol).toUpperCase());
    }
    for (const position of practice?.items ?? []) {
      const quote = markets.find((market) => market.symbol.toUpperCase() === position.symbol.toUpperCase());
      symbols.add((quote?.base_symbol ?? position.symbol).toUpperCase());
    }
    return [...symbols];
  }, [markets, positions, practice]);

  useEffect(() => {
    if (!selectionReady || !data || (!practice && !practiceError)) return;
    if (hasSavedSelection && chartSymbols.includes(selectedSymbol)) return;
    if (hasSavedSelection && !chartSymbols.length) return;
    const preferredPosition = practice?.items[0] ?? positions[0];
    const matchingMarket = preferredPosition
      ? markets.find((market) => market.symbol.toUpperCase() === preferredPosition.symbol.toUpperCase())
      : undefined;
    const preferred = matchingMarket?.base_symbol ?? preferredPosition?.symbol ?? chartSymbols[0] ?? "EURUSD";
    setSelectedSymbol(preferred.toUpperCase());
  }, [chartSymbols, data, hasSavedSelection, markets, positions, practice, practiceError, selectedSymbol, selectionReady, setSelectedSymbol]);

  const simulated = data?.simulated ?? true;
  const chartOptions = chartSymbols.length ? chartSymbols : [selectedSymbol];
  const canPracticeSelectedSymbol = practiceSymbols.has(selectedSymbol.toUpperCase());
  const chartPositions = useMemo(() => [
    ...(practice?.items ?? [])
      .filter((position) => {
        const market = markets.find((item) => item.symbol.toUpperCase() === position.symbol.toUpperCase());
        return (market?.base_symbol ?? position.symbol).toUpperCase() === selectedSymbol.toUpperCase();
      })
      .map((position) => ({ ...position, source: "PRACTICE" as const })),
    ...(!data?.simulated ? positions
      .filter((position) => {
        const market = markets.find((item) => item.symbol.toUpperCase() === position.symbol.toUpperCase());
        return (market?.base_symbol ?? position.symbol).toUpperCase() === selectedSymbol.toUpperCase();
      })
      .map((position) => ({ ...position, source: "BROKER" as const })) : []),
  ], [data?.simulated, markets, positions, practice?.items, selectedSymbol]);

  return (
    <div className="positions-workspace">
      <div className="positions-terminal">
        <LiveMarketChart
          symbol={selectedSymbol}
          symbols={chartOptions}
          positions={chartPositions}
          onSymbolChange={(symbol) => {
            setSelectedSymbol(symbol);
          }}
        />
        {canPracticeSelectedSymbol ? (
          <>
            <QuickTradePanel
              symbol={selectedSymbol}
              onSubmitted={() => setRefreshVersion((version) => version + 1)}
            />
            <section className="card positions-advanced-ticket">
              <div>
                <strong>Advanced order ticket</strong>
                <p>Place buy/sell stops or add optional stop loss and take profit.</p>
              </div>
              <SimulationTradeTicket
                key={selectedSymbol}
                initialSymbol={selectedSymbol}
                triggerLabel="Open advanced ticket"
                triggerDescription="Stop orders · optional protection levels"
                onSubmitted={(tradedSymbol) => {
                  if (tradedSymbol) setSelectedSymbol(tradedSymbol);
                  setRefreshVersion((version) => version + 1);
                }}
              />
            </section>
          </>
        ) : (
          <section className="card positions-trade-unavailable">
            <strong>{selectedSymbol} is view-only in practice mode</strong>
            <p>Choose a practice-supported instrument to place simulated trades. Broker orders remain read-only.</p>
          </section>
        )}
      </div>

      <section className="card positions-panel">
        <div className="positions-toolbar">
          <div>
            <strong>{practice ? `${practice.total} open practice ${practice.total === 1 ? "position" : "positions"}` : "Practice positions"}</strong>
            <p>{practice ? `${practice.account.currency} ${practice.account.balance} virtual balance · independent of your broker` : "Loading independent virtual account…"}</p>
          </div>
          <span className="pill simulation-pill">PRACTICE ONLY</span>
        </div>
        {practiceError && <p className="error-text positions-error" role="alert">{practiceError}</p>}
        {!practice ? (
          <div className="empty positions-empty">Practice positions are unavailable right now.</div>
        ) : practice.items.length === 0 ? (
          <div className="empty positions-empty">No open practice positions. Place one from the chart above.</div>
        ) : (
          <PracticePositionsManager
            positions={practice.items}
            onUpdated={() => setRefreshVersion((version) => version + 1)}
          />
        )}
        {practice && practice.pending_total > 0 && (
          <div className="positions-table-wrap positions-pending-wrap">
            <div className="positions-subheading"><strong>{practice.pending_total} pending stop {practice.pending_total === 1 ? "order" : "orders"}</strong><span>Waiting for trigger price</span></div>
            <table className="table positions-table positions-pending-table">
              <thead><tr><th>Order</th><th>Instrument</th><th>Side</th><th>Volume</th><th>Trigger price</th><th>Stop loss</th><th>Take profit</th></tr></thead>
              <tbody>
                {practice.pending_orders.map((order) => (
                  <tr key={order.ticket}>
                    <td>{order.order_type.replace("_", " ")}</td>
                    <td><strong>{order.symbol}</strong></td>
                    <td>{order.direction}</td>
                    <td>{order.volume}</td>
                    <td>{order.stop_price}</td>
                    <td>{Number(order.stop_loss) > 0 ? order.stop_loss : "—"}</td>
                    <td>{Number(order.take_profit) > 0 ? order.take_profit : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="card positions-panel">
        <div className="positions-toolbar">
          <div>
            <strong>{data?.connected ? `${data.total} open broker ${data.total === 1 ? "position" : "positions"}` : "Broker disconnected"}</strong>
            <p>Read-only snapshot · refreshing every 5 seconds</p>
          </div>
          <span className={`pill ${simulated ? "simulation-pill" : "broker-pill"}`}>
            {simulated ? "SIMULATION" : "MT5 · READ ONLY"}
          </span>
        </div>
        {error && <p className="error-text positions-error" role="alert">{error}</p>}
        {!data?.connected ? (
          <div className="empty positions-empty">Connect an account to read its broker positions. The practice account remains available independently.</div>
        ) : positions.length === 0 ? (
          <div className="empty positions-empty">No open broker positions.</div>
        ) : (
          <div className="positions-table-wrap">
            <table className="table positions-table">
              <thead>
                <tr><th>Ticket</th><th>Instrument</th><th>Side</th><th>Volume</th><th>Open price</th><th>Current price</th><th>Floating P/L</th><th>Stop loss</th><th>Take profit</th></tr>
              </thead>
              <tbody>
                {positions.map((position) => (
                  <tr key={position.ticket}>
                    <td>{position.ticket}</td>
                    <td><strong>{position.symbol}</strong></td>
                    <td><span className={`signal-direction ${position.direction === "BUY" ? "buy-direction" : "sell-direction"}`}>{position.direction}</span></td>
                    <td>{position.volume}</td>
                    <td>{position.price_open}</td>
                    <td>{position.price_current}</td>
                    <td className={Number(position.profit) >= 0 ? "position-profit" : "position-loss"}>{position.profit}</td>
                    <td>{Number(position.stop_loss) > 0 ? position.stop_loss : "—"}</td>
                    <td>{Number(position.take_profit) > 0 ? position.take_profit : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <p className="safety-note positions-safety">
          Broker positions are read-only. Practice trades are virtual and remain separate from your connected account.
        </p>
      </section>
    </div>
  );
}
