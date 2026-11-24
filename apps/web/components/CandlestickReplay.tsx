"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type {
  IChartApi,
  IPriceLine,
  ISeriesApi,
  ISeriesMarkersPluginApi,
  SeriesMarker,
  Time,
  UTCTimestamp,
} from "lightweight-charts";

export type ReplayCandle = {
  time: string;
  open: string;
  high: string;
  low: string;
  close: string;
  volume: string;
};

export type ReplayMarker = {
  time: string;
  direction: "BUY" | "SELL";
  kind: "entry" | "exit";
  label: string;
};

export type PositionOverlay = {
  ticket: string;
  symbol?: string;
  direction: "BUY" | "SELL";
  volume: string;
  price_open: string;
  price_current: string;
  profit: string;
  stop_loss: string;
  take_profit: string;
  source?: "PRACTICE" | "BROKER";
};

type Props = {
  candles: ReplayCandle[];
  markers: ReplayMarker[];
  visibleCount: number;
  live?: boolean;
  positions?: PositionOverlay[];
  timeframeOptions?: readonly string[];
  activeTimeframe?: string;
  onTimeframeChange?: (timeframe: string) => void;
};

function toTimestamp(value: string): UTCTimestamp {
  return Math.floor(Date.parse(value) / 1000) as UTCTimestamp;
}

function sameCandle(left: ReplayCandle, right: ReplayCandle): boolean {
  return left.time === right.time
    && left.open === right.open
    && left.high === right.high
    && left.low === right.low
    && left.close === right.close
    && left.volume === right.volume;
}

export function CandlestickReplay({
  candles,
  markers,
  visibleCount,
  live = false,
  positions = [],
  timeframeOptions,
  activeTimeframe,
  onTimeframeChange,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const markersRef = useRef<ISeriesMarkersPluginApi<Time> | null>(null);
  const positionLinesRef = useRef<IPriceLine[]>([]);
  const timeframeOptionsRef = useRef(timeframeOptions);
  const onTimeframeChangeRef = useRef(onTimeframeChange);
  const renderedRef = useRef<{ candles: ReplayCandle[]; visibleCount: number } | null>(null);
  const [chartReady, setChartReady] = useState(false);
  const [chartError, setChartError] = useState("");
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [timeframeMenuPoint, setTimeframeMenuPoint] = useState<{ x: number; y: number; width: number; height: number } | null>(null);
  const chartCandles = useMemo(() => candles.map((candle) => ({
    time: toTimestamp(candle.time),
    open: Number(candle.open),
    high: Number(candle.high),
    low: Number(candle.low),
    close: Number(candle.close),
  })), [candles]);
  const candleIndexes = useMemo(
    () => new Map(chartCandles.map((candle, index) => [Number(candle.time), index] as const)),
    [chartCandles],
  );
  const activePositionMarkers = useMemo<ReplayMarker[]>(() => {
    const latestCandle = candles.at(-1);
    if (!live || !latestCandle) return [];
    return positions.map((position) => ({
      time: latestCandle.time,
      direction: position.direction,
      kind: "entry",
      label: `${position.source === "BROKER" ? "MT5" : "PRACTICE"} ${position.direction} OPEN`,
      } satisfies ReplayMarker));
  }, [candles, live, positions]);
  const chartMarkers = useMemo(() => [...markers, ...activePositionMarkers].flatMap((marker) => {
    const time = toTimestamp(marker.time);
    const candleIndex = candleIndexes.get(Number(time));
    if (candleIndex === undefined) return [];
    const isEntry = marker.kind === "entry";
    const position: SeriesMarker<Time>["position"] = isEntry
      ? marker.direction === "BUY" ? "belowBar" : "aboveBar"
      : marker.direction === "BUY" ? "aboveBar" : "belowBar";
    const shape: SeriesMarker<Time>["shape"] = isEntry
      ? marker.direction === "BUY" ? "arrowUp" : "arrowDown"
      : "circle";
    return [{
      candleIndex,
      marker: {
        time,
        position,
        shape,
        color: marker.label === "SL" ? "#ef6270" : marker.label === "TP" ? "#2ac79a" : "#6ebcff",
        text: marker.label,
      } satisfies SeriesMarker<Time>,
    }];
  }), [activePositionMarkers, markers, candleIndexes]);

  useEffect(() => {
    timeframeOptionsRef.current = timeframeOptions;
    onTimeframeChangeRef.current = onTimeframeChange;
  }, [timeframeOptions, onTimeframeChange]);

  function zoomTimeScale(factor: number) {
    const timeScale = chartRef.current?.timeScale();
    const range = timeScale?.getVisibleLogicalRange();
    if (!timeScale || !range) return;
    const center = (range.from + range.to) / 2;
    const width = Math.max(8, Math.min(candles.length, (range.to - range.from) * factor));
    timeScale.setVisibleLogicalRange({ from: center - width / 2, to: center + width / 2 });
  }

  function resetZoom() {
    chartRef.current?.timeScale().fitContent();
  }

  useEffect(() => {
    if (!isFullscreen) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    function exitFullscreen(event: KeyboardEvent) {
      if (event.key === "Escape") setIsFullscreen(false);
    }
    window.addEventListener("keydown", exitFullscreen);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", exitFullscreen);
    };
  }, [isFullscreen]);

  useEffect(() => {
    if (!timeframeMenuPoint) return;
    function closeTimeframeMenu(event: KeyboardEvent) {
      if (event.key === "Escape") setTimeframeMenuPoint(null);
    }
    function closeOnOutsidePointer(event: PointerEvent) {
      if (event.target instanceof Node && !containerRef.current?.contains(event.target)) {
        setTimeframeMenuPoint(null);
      }
    }
    window.addEventListener("keydown", closeTimeframeMenu);
    window.addEventListener("pointerdown", closeOnOutsidePointer);
    return () => {
      window.removeEventListener("keydown", closeTimeframeMenu);
      window.removeEventListener("pointerdown", closeOnOutsidePointer);
    };
  }, [timeframeMenuPoint]);

  useEffect(() => {
    let active = true;
    let resizeObserver: ResizeObserver | null = null;

    void import("lightweight-charts").then(({ createChart, CandlestickSeries, createSeriesMarkers }) => {
      const container = containerRef.current;
      if (!active || !container) return;

      const chart = createChart(container, {
        width: container.clientWidth,
        height: container.clientHeight || 380,
        layout: {
          background: { color: "#0b1118" },
          textColor: "#aab6c5",
          attributionLogo: true,
        },
        grid: {
          vertLines: { color: "#18232e" },
          horzLines: { color: "#18232e" },
        },
        rightPriceScale: { borderColor: "#263442" },
        timeScale: { borderColor: "#263442", timeVisible: true, secondsVisible: false, barSpacing: 8, rightOffset: 8 },
        handleScale: { mouseWheel: true, pinch: true, axisDoubleClickReset: true },
        handleScroll: { mouseWheel: true, pressedMouseMove: true, horzTouchDrag: true },
        crosshair: {
          vertLine: { color: "#728093", labelBackgroundColor: "#243444" },
          horzLine: { color: "#728093", labelBackgroundColor: "#243444" },
        },
      });
      const candleSeries = chart.addSeries(CandlestickSeries, {
        upColor: "#2ac79a",
        downColor: "#ef6270",
        borderUpColor: "#2ac79a",
        borderDownColor: "#ef6270",
        wickUpColor: "#2ac79a",
        wickDownColor: "#ef6270",
      });

      chartRef.current = chart;
      candleSeriesRef.current = candleSeries;
      markersRef.current = createSeriesMarkers(candleSeries, []);
      chart.subscribeClick((event) => {
        if (!timeframeOptionsRef.current?.length || !onTimeframeChangeRef.current || !event.point) return;
        setTimeframeMenuPoint({
          x: event.point.x,
          y: event.point.y,
          width: container.clientWidth,
          height: container.clientHeight,
        });
      });
      resizeObserver = new ResizeObserver((entries) => {
        const width = entries[0]?.contentRect.width;
        const height = entries[0]?.contentRect.height;
        if (width && height) chart.applyOptions({ width: Math.floor(width), height: Math.floor(height) });
      });
      resizeObserver.observe(container);
      setChartReady(true);
    }).catch((cause: unknown) => {
      if (active) {
        setChartError(cause instanceof Error ? cause.message : "Candlestick chart failed to load");
      }
    });

    return () => {
      active = false;
      resizeObserver?.disconnect();
      const series = candleSeriesRef.current;
      if (series) {
        for (const line of positionLinesRef.current) series.removePriceLine(line);
        positionLinesRef.current = [];
      }
      chartRef.current?.remove();
      chartRef.current = null;
      candleSeriesRef.current = null;
      markersRef.current = null;
      positionLinesRef.current = [];
    };
  }, []);

  useEffect(() => {
    const chart = chartRef.current;
    const candleSeries = candleSeriesRef.current;
    if (!chartReady || !chart || !candleSeries || candles.length === 0) return;

    const previous = renderedRef.current;
    if (live) {
      const previousCandles = previous?.candles.slice(0, previous.visibleCount) ?? [];
      const visibleRange = chart.timeScale().getVisibleLogicalRange();
      const followsLatest = !visibleRange || visibleRange.to >= previousCandles.length - 2;
      const unchangedBeforeLast = previousCandles.length > 0
        && previousCandles.length <= candles.length
        && previousCandles.slice(0, -1).every((candle, index) => sameCandle(candle, candles[index]));

      if (!previous) {
        candleSeries.setData(chartCandles);
        chart.timeScale().setVisibleLogicalRange({
          from: Math.max(0, chartCandles.length - 100),
          to: chartCandles.length + 8,
        });
      } else if (
        unchangedBeforeLast
        && previousCandles.length === candles.length
        && previousCandles.at(-1)?.time === candles.at(-1)?.time
      ) {
        if (!sameCandle(previousCandles[previousCandles.length - 1], candles[candles.length - 1])) {
          candleSeries.update(chartCandles[chartCandles.length - 1]);
        }
      } else if (
        unchangedBeforeLast
        && candles.length === previousCandles.length + 1
        && previousCandles.at(-1)?.time === candles.at(-2)?.time
      ) {
        candleSeries.update(chartCandles[chartCandles.length - 2]);
        candleSeries.update(chartCandles[chartCandles.length - 1]);
        if (followsLatest) chart.timeScale().scrollToRealTime();
      } else {
        candleSeries.setData(chartCandles);
        if (followsLatest) chart.timeScale().scrollToRealTime();
      }
    } else if (previous?.candles === candles && visibleCount === previous.visibleCount + 1 && visibleCount > 0) {
      candleSeries.update(chartCandles[visibleCount - 1]);
    } else {
      candleSeries.setData(chartCandles.slice(0, visibleCount));
    }
    renderedRef.current = { candles, visibleCount };

    const visibleMarkers = chartMarkers
      .filter(({ candleIndex }) => candleIndex < visibleCount)
      .map(({ marker }) => marker);
    markersRef.current?.setMarkers(visibleMarkers);

    chart.timeScale().scrollToRealTime();
  }, [candles, chartCandles, chartMarkers, visibleCount, chartReady, live]);

  useEffect(() => {
    const series = candleSeriesRef.current;
    if (!chartReady || !series) return;
    for (const line of positionLinesRef.current) series.removePriceLine(line);
    positionLinesRef.current = [];

    for (const position of positions) {
      const directionColor = position.direction === "BUY" ? "#61b8e4" : "#ed8d91";
      const sourceLabel = position.source === "BROKER" ? "BROKER" : "PRACTICE";
      const lines = [
        { price: Number(position.price_open), title: `${sourceLabel} ${position.direction} ${position.volume} · OPEN`, color: directionColor, lineStyle: 2 },
        { price: Number(position.price_current), title: `${sourceLabel} · LIVE ${position.profit}`, color: directionColor, lineStyle: 1 },
        ...(Number(position.stop_loss) > 0
          ? [{ price: Number(position.stop_loss), title: `${sourceLabel} SL · ${position.ticket.slice(-6)}`, color: "#ef6270", lineStyle: 2 }]
          : []),
        ...(Number(position.take_profit) > 0
          ? [{ price: Number(position.take_profit), title: `${sourceLabel} TP · ${position.ticket.slice(-6)}`, color: "#2ac79a", lineStyle: 2 }]
          : []),
      ];
      for (const line of lines) {
        if (!Number.isFinite(line.price) || line.price <= 0) continue;
        positionLinesRef.current.push(series.createPriceLine({
          price: line.price,
          color: line.color,
          lineWidth: 1,
          lineStyle: line.lineStyle,
          axisLabelVisible: true,
          title: line.title,
        }));
      }
    }

    return () => {
      if (candleSeriesRef.current !== series) return;
      for (const line of positionLinesRef.current) series.removePriceLine(line);
      positionLinesRef.current = [];
    };
  }, [positions, chartReady]);

  const currentCandle = candles[Math.max(0, visibleCount - 1)];
  const timeframeMenuCenter = timeframeMenuPoint
    ? {
      x: Math.max(58, Math.min(timeframeMenuPoint.width - 58, timeframeMenuPoint.x)),
      y: Math.max(58, Math.min(timeframeMenuPoint.height - 58, timeframeMenuPoint.y)),
    }
    : null;

  return (
    <section className={`card replay-chart-panel${isFullscreen ? " replay-chart-fullscreen" : ""}${live ? " live-market-chart-panel" : ""}`}>
      {currentCandle && (
        <div className="replay-chart-heading">
          <div className="replay-chart-context">
            <strong>{new Date(currentCandle.time).toLocaleString()}</strong>
            <span>Scroll or pinch to zoom · drag to pan</span>
          </div>
          <div className="replay-ohlc">
            <span>O {currentCandle.open}</span>
            <span>H {currentCandle.high}</span>
            <span>L {currentCandle.low}</span>
            <span>C {currentCandle.close}</span>
          </div>
          <div className="replay-zoom-controls" role="group" aria-label="Chart zoom controls">
            <button type="button" onClick={() => zoomTimeScale(0.7)} aria-label="Zoom in" title="Zoom in">+</button>
            <button type="button" onClick={() => zoomTimeScale(1.4)} aria-label="Zoom out" title="Zoom out">−</button>
            <button className="replay-fit-button" type="button" onClick={resetZoom} aria-label="Fit chart to view" title="Fit chart">Fit</button>
            <button type="button" onClick={() => setIsFullscreen((current) => !current)} aria-label={isFullscreen ? "Exit full screen chart" : "Open full screen chart"} aria-pressed={isFullscreen}>
              {isFullscreen ? "Exit" : "Full screen"}
            </button>
          </div>
        </div>
      )}
      {chartError ? (
        <p className="error-text" role="alert">Candlestick chart unavailable: {chartError}</p>
      ) : (
        <div className="replay-chart-canvas" ref={containerRef} aria-label={live ? "Live market candlestick chart" : "Historical candlestick replay chart"}>
          {timeframeMenuPoint && timeframeOptions?.length && onTimeframeChange && (
            <div className="chart-timeframe-radial" role="group" aria-label="Quick timeframe selector">
              {timeframeMenuCenter && timeframeOptions.map((timeframe, index) => {
                const angle = -Math.PI / 2 + (index * Math.PI * 2) / timeframeOptions.length;
                const left = timeframeMenuCenter.x + Math.cos(angle) * 62 - 23;
                const top = timeframeMenuCenter.y + Math.sin(angle) * 62 - 17;
                return (
                  <button
                    key={timeframe}
                    className={`chart-timeframe-option${timeframe === activeTimeframe ? " selected" : ""}`}
                    type="button"
                    style={{ left, top }}
                    aria-label={`Set timeframe to ${timeframe}`}
                    aria-pressed={timeframe === activeTimeframe}
                    onClick={(event) => {
                      event.stopPropagation();
                      onTimeframeChange(timeframe);
                      setTimeframeMenuPoint(null);
                    }}
                  >
                    {timeframe}
                  </button>
                );
              })}
              <button
                type="button"
                className="chart-timeframe-center"
                style={timeframeMenuCenter ? { left: timeframeMenuCenter.x - 20, top: timeframeMenuCenter.y - 20 } : undefined}
                aria-label="Close timeframe selector"
                onClick={(event) => {
                  event.stopPropagation();
                  setTimeframeMenuPoint(null);
                }}
              >
                {activeTimeframe ?? "TF"}
              </button>
            </div>
          )}
        </div>
      )}
      <a className="chart-attribution" href="https://www.tradingview.com/" target="_blank" rel="noreferrer">
        Charts powered by TradingView Lightweight Charts™
      </a>
    </section>
  );
}
