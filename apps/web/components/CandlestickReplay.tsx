"use client";

import { useEffect, useRef, useState } from "react";
import type {
  IChartApi,
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

type Props = {
  candles: ReplayCandle[];
  markers: ReplayMarker[];
  visibleCount: number;
};

function toTimestamp(value: string): UTCTimestamp {
  return Math.floor(Date.parse(value) / 1000) as UTCTimestamp;
}

export function CandlestickReplay({ candles, markers, visibleCount }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const markersRef = useRef<ISeriesMarkersPluginApi<Time> | null>(null);
  const [chartReady, setChartReady] = useState(false);
  const [chartError, setChartError] = useState("");

  useEffect(() => {
    let active = true;
    let resizeObserver: ResizeObserver | null = null;

    void import("lightweight-charts").then(({ createChart, CandlestickSeries, createSeriesMarkers }) => {
      const container = containerRef.current;
      if (!active || !container) return;

      const chart = createChart(container, {
        width: container.clientWidth,
        height: 380,
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
      resizeObserver = new ResizeObserver((entries) => {
        const width = entries[0]?.contentRect.width;
        if (width) chart.applyOptions({ width: Math.floor(width) });
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
      chartRef.current?.remove();
      chartRef.current = null;
      candleSeriesRef.current = null;
      markersRef.current = null;
    };
  }, []);

  useEffect(() => {
    const chart = chartRef.current;
    const candleSeries = candleSeriesRef.current;
    if (!chartReady || !chart || !candleSeries || candles.length === 0) return;

    const visibleCandles = candles.slice(0, visibleCount);
    candleSeries.setData(visibleCandles.map((candle) => ({
      time: toTimestamp(candle.time),
      open: Number(candle.open),
      high: Number(candle.high),
      low: Number(candle.low),
      close: Number(candle.close),
    })));

    const visibleTimes = new Set(visibleCandles.map((candle) => toTimestamp(candle.time)));
    const visibleMarkers: SeriesMarker<Time>[] = markers.flatMap((marker) => {
      const time = toTimestamp(marker.time);
      if (!visibleTimes.has(time)) return [];
      const isEntry = marker.kind === "entry";
      return [{
        time,
        position: isEntry
          ? marker.direction === "BUY" ? "belowBar" : "aboveBar"
          : marker.direction === "BUY" ? "aboveBar" : "belowBar",
        shape: isEntry
          ? marker.direction === "BUY" ? "arrowUp" : "arrowDown"
          : "circle",
        color: marker.label === "SL" ? "#ef6270" : marker.label === "TP" ? "#2ac79a" : "#6ebcff",
        text: marker.label,
      }];
    });
    markersRef.current?.setMarkers(visibleMarkers);

    chart.timeScale().scrollToRealTime();
  }, [candles, markers, visibleCount, chartReady]);

  const currentCandle = candles[Math.max(0, visibleCount - 1)];

  return (
    <section className="card replay-chart-panel">
      {currentCandle && (
        <div className="replay-chart-heading">
          <strong>{new Date(currentCandle.time).toLocaleString()}</strong>
          <div className="replay-ohlc">
            <span>O {currentCandle.open}</span>
            <span>H {currentCandle.high}</span>
            <span>L {currentCandle.low}</span>
            <span>C {currentCandle.close}</span>
          </div>
        </div>
      )}
      {chartError ? (
        <p className="error-text" role="alert">Candlestick chart unavailable: {chartError}</p>
      ) : (
        <div className="replay-chart-canvas" ref={containerRef} aria-label="Historical candlestick replay chart" />
      )}
      <a className="chart-attribution" href="https://www.tradingview.com/" target="_blank" rel="noreferrer">
        Charts powered by TradingView Lightweight Charts™
      </a>
    </section>
  );
}
