"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { startVisiblePolling } from "@/services/polling";

type BrokerDeal = {
  ticket: string;
  order: string;
  symbol: string;
  direction: "BUY" | "SELL" | "OTHER";
  volume: string;
  price: string;
  profit: string;
  commission: string;
  swap: string;
  time: string;
  net_profit: string;
  deal_type?: "ENTRY" | "EXIT";
};

type HistoryData = {
  items: BrokerDeal[];
  connected: boolean;
  currency: string;
  simulated: boolean;
  period_days: number;
};

type DailyResult = {
  date: Date;
  key: string;
  deals: number;
  net: number;
  cumulative: number;
};

const chart = { width: 720, height: 236, left: 48, right: 12, top: 16, bottom: 34 };
const dayCount = 30;

function dateKey(date: Date): string {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

function aggregateDeals(items: BrokerDeal[]): Map<string, { deals: number; net: number }> {
  const totals = new Map<string, { deals: number; net: number }>();
  for (const item of items) {
    const date = new Date(item.time);
    const net = Number(item.net_profit);
    if (!Number.isFinite(date.getTime()) || !Number.isFinite(net)) {
      throw new Error("Broker history contains an invalid deal date or net result");
    }
    const key = dateKey(date);
    const total = totals.get(key) ?? { deals: 0, net: 0 };
    total.deals += 1;
    total.net += net;
    totals.set(key, total);
  }
  return totals;
}

function buildDailyResults(items: BrokerDeal[], now = new Date()): DailyResult[] {
  const end = new Date(now);
  end.setHours(0, 0, 0, 0);
  const first = new Date(end);
  first.setDate(first.getDate() - dayCount + 1);
  const totals = aggregateDeals(items);

  for (let offset = 0; offset < dayCount; offset += 1) {
    const date = new Date(first);
    date.setDate(first.getDate() + offset);
    const total = totals.get(dateKey(date)) ?? { deals: 0, net: 0 };
    totals.set(dateKey(date), total);
  }

  let cumulative = 0;
  return Array.from({ length: dayCount }, (_, offset) => {
    const date = new Date(first);
    date.setDate(first.getDate() + offset);
    const key = dateKey(date);
    const total = totals.get(key) ?? { deals: 0, net: 0 };
    cumulative += total.net;
    return { key, date, ...total, cumulative };
  });
}

function formatAmount(value: number, currency: string): string {
  const amount = Math.abs(value).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return `${currency ? `${currency} ` : ""}${value < 0 ? "−" : value > 0 ? "+" : ""}${amount}`;
}

function formatCalendarAmount(value: number): string {
  const amount = Math.abs(value).toLocaleString(undefined, { notation: "compact", maximumFractionDigits: 1 });
  return `${value < 0 ? "−" : value > 0 ? "+" : ""}${amount}`;
}

function formatDealAmount(value: string, currency: string): string {
  const amount = Number(value);
  return Number.isFinite(amount) ? formatAmount(amount, currency) : "—";
}

function BarChart({ days, currency }: { days: DailyResult[]; currency: string }) {
  const values = days.map((day) => day.net);
  const maximum = Math.max(...values, 0);
  const minimum = Math.min(...values, 0);
  const spread = maximum - minimum || 1;
  const plotHeight = chart.height - chart.top - chart.bottom;
  const plotWidth = chart.width - chart.left - chart.right;
  const zeroY = maximum === minimum ? chart.top + plotHeight / 2 : chart.top + maximum / spread * plotHeight;
  const slot = plotWidth / days.length;

  return (
    <svg className="performance-chart-svg" viewBox={`0 0 ${chart.width} ${chart.height}`} preserveAspectRatio="none" role="img" aria-label="Daily realized broker deal net profit and loss for the last 30 days">
      <line className="performance-gridline" x1={chart.left} x2={chart.width - chart.right} y1={chart.top} y2={chart.top} />
      <line className="performance-zero-line" x1={chart.left} x2={chart.width - chart.right} y1={zeroY} y2={zeroY} />
      <line className="performance-gridline" x1={chart.left} x2={chart.width - chart.right} y1={chart.height - chart.bottom} y2={chart.height - chart.bottom} />
      <text className="performance-axis-label" x="2" y={chart.top + 4}>{formatAmount(maximum, currency)}</text>
      <text className="performance-axis-label" x="2" y={chart.height - chart.bottom + 3}>{formatAmount(minimum, currency)}</text>
      {days.map((day, index) => {
        const x = chart.left + slot * index + slot * 0.22;
        const valueHeight = Math.abs(day.net) / spread * plotHeight;
        const y = day.net >= 0 ? zeroY - valueHeight : zeroY;
        const labelEvery = index % 5 === 0 || index === days.length - 1;
        return (
          <g key={day.key}>
            <rect
              className={day.net > 0 ? "performance-bar positive" : day.net < 0 ? "performance-bar negative" : "performance-bar neutral"}
              x={x}
              y={day.net === 0 ? zeroY - 1 : y}
              width={slot * 0.56}
              height={Math.max(valueHeight, 1)}
              rx="3"
            >
              <title>{`${day.date.toLocaleDateString()}: ${formatAmount(day.net, currency)} · ${day.deals} deals`}</title>
            </rect>
            {labelEvery && <text className="performance-day-label" x={chart.left + slot * (index + 0.5)} y={chart.height - 10}>{day.date.toLocaleDateString(undefined, { month: "short", day: "numeric" })}</text>}
          </g>
        );
      })}
    </svg>
  );
}

function CumulativeChart({ days, currency }: { days: DailyResult[]; currency: string }) {
  const values = days.map((day) => day.cumulative);
  const minimum = Math.min(0, ...values);
  const maximum = Math.max(0, ...values);
  const spread = maximum - minimum || 1;
  const plotHeight = chart.height - chart.top - chart.bottom;
  const plotWidth = chart.width - chart.left - chart.right;
  const zeroY = maximum === minimum ? chart.top + plotHeight / 2 : chart.top + (maximum / spread) * plotHeight;
  const points = days.map((day, index) => ({
    day,
    x: chart.left + plotWidth * index / Math.max(days.length - 1, 1),
    y: maximum === minimum ? chart.top + plotHeight / 2 : chart.top + (maximum - day.cumulative) / spread * plotHeight,
  }));
  const line = points.map((point) => `${point.x},${point.y}`).join(" ");
  const area = `${points[0].x},${zeroY} ${line} ${points[points.length - 1].x},${zeroY}`;

  return (
    <svg className="performance-chart-svg" viewBox={`0 0 ${chart.width} ${chart.height}`} preserveAspectRatio="none" role="img" aria-label="Cumulative realized broker deal net profit and loss for the last 30 days">
      <line className="performance-gridline" x1={chart.left} x2={chart.width - chart.right} y1={chart.top} y2={chart.top} />
      <line className="performance-zero-line" x1={chart.left} x2={chart.width - chart.right} y1={zeroY} y2={zeroY} />
      <line className="performance-gridline" x1={chart.left} x2={chart.width - chart.right} y1={chart.height - chart.bottom} y2={chart.height - chart.bottom} />
      <text className="performance-axis-label" x="2" y={chart.top + 4}>{formatAmount(maximum, currency)}</text>
      <text className="performance-axis-label" x="2" y={chart.height - chart.bottom + 3}>{formatAmount(minimum, currency)}</text>
      <polygon className="performance-area" points={area} />
      <polyline className="performance-line" points={line} />
      {points.map((point, index) => (
        index % 2 === 0 || index === points.length - 1
          ? <circle className="performance-point" key={point.day.key} cx={point.x} cy={point.y} r="3"><title>{`${point.day.date.toLocaleDateString()}: ${formatAmount(point.day.cumulative, currency)} cumulative`}</title></circle>
          : null
      ))}
    </svg>
  );
}

function PerformanceCalendar({
  month,
  dailyTotals,
  connected,
  currency,
  periodDays,
  selectedDay,
  onSelectDay,
  onChangeMonth,
}: {
  month: Date;
  dailyTotals: Map<string, { deals: number; net: number }>;
  connected: boolean;
  currency: string;
  periodDays: number;
  selectedDay: string;
  onSelectDay: (key: string) => void;
  onChangeMonth: (offset: number) => void;
}) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const historyStart = new Date(today);
  historyStart.setDate(historyStart.getDate() - periodDays + 1);
  const firstDay = new Date(month.getFullYear(), month.getMonth(), 1);
  const daysInMonth = new Date(month.getFullYear(), month.getMonth() + 1, 0).getDate();
  const leadingDays = firstDay.getDay();
  const calendarSize = Math.ceil((leadingDays + daysInMonth) / 7) * 7;
  const dates = Array.from({ length: calendarSize }, (_, index) => {
    const day = index - leadingDays + 1;
    return day >= 1 && day <= daysInMonth
      ? new Date(month.getFullYear(), month.getMonth(), day)
      : null;
  });
  const monthKey = month.getFullYear() * 12 + month.getMonth();
  const earliestMonthKey = historyStart.getFullYear() * 12 + historyStart.getMonth();
  const currentMonthKey = today.getFullYear() * 12 + today.getMonth();
  const monthDeals = dates.reduce((total, date) => {
    if (!date || date < historyStart || date > today) return total;
    return total + (dailyTotals.get(dateKey(date))?.deals ?? 0);
  }, 0);
  const monthNet = dates.reduce((total, date) => {
    if (!date || date < historyStart || date > today) return total;
    return total + (dailyTotals.get(dateKey(date))?.net ?? 0);
  }, 0);
  const selectedDate = new Date(`${selectedDay}T00:00:00`);
  const selectedIsAvailable = connected && selectedDate >= historyStart && selectedDate <= today;
  const selectedTotal = dailyTotals.get(selectedDay);
  const monthLabel = month.toLocaleDateString(undefined, { month: "long", year: "numeric" });

  return (
    <section className="performance-calendar" aria-labelledby="performance-calendar-title">
      <div className="performance-calendar-heading">
        <div>
          <h3 id="performance-calendar-title">Performance calendar</h3>
          <p>Daily realized results · your local time</p>
        </div>
        <div className="calendar-navigation">
          <button type="button" aria-label="Previous month" disabled={monthKey <= earliestMonthKey} onClick={() => onChangeMonth(-1)}>
            <svg viewBox="0 0 20 20" aria-hidden="true"><path d="m12 4-6 6 6 6" /></svg>
          </button>
          <strong aria-live="polite">{monthLabel}</strong>
          <button type="button" aria-label="Next month" disabled={monthKey >= currentMonthKey} onClick={() => onChangeMonth(1)}>
            <svg viewBox="0 0 20 20" aria-hidden="true"><path d="m8 4 6 6-6 6" /></svg>
          </button>
        </div>
      </div>

      <div className="performance-calendar-summary">
        <div><span>Month net</span><strong className={monthNet < 0 ? "position-loss" : monthNet > 0 ? "position-profit" : ""}>{connected ? formatAmount(monthNet, currency) : "—"}</strong></div>
        <div><span>Closed deals</span><strong>{connected ? monthDeals.toLocaleString() : "—"}</strong></div>
        <div className="calendar-legend" aria-label="Calendar color legend">
          <span><i className="legend-positive" /> Profit</span>
          <span><i className="legend-negative" /> Loss</span>
          <span><i className="legend-neutral" /> No trades</span>
        </div>
      </div>

      <div className="performance-calendar-grid" role="group" aria-label={`${monthLabel} daily trading performance`}>
        {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((day) => (
          <span className="performance-calendar-weekday" key={day}>{day}</span>
        ))}
        {dates.map((date, index) => {
          if (!date) return <span className="performance-calendar-blank" aria-hidden="true" key={`blank-${index}`} />;
          const key = dateKey(date);
          const future = date > today;
          const available = connected && date >= historyStart && !future;
          const total = dailyTotals.get(key) ?? { deals: 0, net: 0 };
          const selected = key === selectedDay;
          const classes = [
            "performance-calendar-day",
            total.deals && total.net > 0 ? "is-positive" : "",
            total.deals && total.net < 0 ? "is-negative" : "",
            total.deals && total.net === 0 ? "has-flat-result" : "",
            available && !total.deals ? "has-no-trades" : "",
            !connected ? "is-unavailable" : "",
            date < historyStart ? "is-out-of-range" : "",
            future ? "is-future" : "",
            dateKey(today) === key ? "is-today" : "",
            selected ? "is-selected" : "",
          ].filter(Boolean).join(" ");
          const status = !connected
            ? "Broker not connected"
            : future
              ? "Upcoming"
              : date < historyStart
                ? "Outside available history"
                : total.deals
                  ? `${total.deals} ${total.deals === 1 ? "deal" : "deals"}`
                  : "No trades";
          const amount = available && total.deals ? formatAmount(total.net, currency) : "—";
          const label = `${date.toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric" })}: ${available && total.deals ? `${amount}, ${status}` : status}`;
          return (
            <button
              className={classes}
              type="button"
              key={key}
              disabled={!available}
              aria-label={label}
              aria-pressed={selected}
              title={label}
              onClick={() => onSelectDay(key)}
            >
              <span className="calendar-day-number">{date.getDate()}</span>
              <span className="calendar-day-result">{available ? (total.deals ? formatCalendarAmount(total.net) : "—") : future ? "Upcoming" : connected ? "Unavailable" : "—"}</span>
              {available && total.deals > 0 && <span className="calendar-day-deals">{total.deals} {total.deals === 1 ? "deal" : "deals"}</span>}
            </button>
          );
        })}
      </div>

      <div className="performance-calendar-selected" aria-live="polite">
        <div>
          <span>Selected day</span>
          <strong>{selectedDate.toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric" })}</strong>
        </div>
        <div>
          <span>{selectedIsAvailable ? `${selectedTotal?.deals ?? 0} closed ${(selectedTotal?.deals ?? 0) === 1 ? "deal" : "deals"}` : connected ? "Outside available history" : "Broker not connected"}</span>
          <strong className={selectedTotal && selectedTotal.net < 0 ? "position-loss" : selectedTotal && selectedTotal.net > 0 ? "position-profit" : ""}>
            {selectedIsAvailable ? formatAmount(selectedTotal?.net ?? 0, currency) : "—"}
          </strong>
        </div>
      </div>
    </section>
  );
}

export function DashboardPerformance() {
  const [history, setHistory] = useState<HistoryData | null>(null);
  const [error, setError] = useState("");
  const [dialogDay, setDialogDay] = useState<string | null>(null);
  const dayTradesDialogRef = useRef<HTMLDialogElement>(null);
  const [calendarMonth, setCalendarMonth] = useState(() => {
    const now = new Date();
    return new Date(now.getFullYear(), now.getMonth(), 1);
  });
  const [selectedDay, setSelectedDay] = useState(() => dateKey(new Date()));

  useEffect(() => {
    const dialog = dayTradesDialogRef.current;
    if (!dialog) return;
    if (dialogDay && !dialog.open) dialog.showModal();
    if (!dialogDay && dialog.open) dialog.close();
  }, [dialogDay]);

  useEffect(() => {
    let active = true;
    async function refresh() {
      try {
        const response = await fetch("/api/v1/history", { cache: "no-store" });
        const result = await response.json() as HistoryData & { detail?: string };
        if (!response.ok) throw new Error(result.detail ?? "Unable to load daily trading performance");
        buildDailyResults(result.items);
        if (active) {
          setHistory(result);
          setError("");
        }
      } catch (cause) {
        if (active) setError(cause instanceof Error ? cause.message : "Trading performance is unavailable");
      }
    }
    const stopPolling = startVisiblePolling(refresh, 30000);
    return () => {
      active = false;
      stopPolling();
    };
  }, []);

  const dailyResults = useMemo(() => buildDailyResults(history?.items ?? []), [history]);
  const dailyTotals = useMemo(() => aggregateDeals(history?.items ?? []), [history]);
  const selectedDayDeals = useMemo(
    () => dialogDay ? (history?.items ?? []).filter((deal) => dateKey(new Date(deal.time)) === dialogDay) : [],
    [dialogDay, history],
  );
  const selectedDayNet = selectedDayDeals.reduce((total, deal) => total + Number(deal.net_profit), 0);
  const dialogDate = dialogDay ? new Date(`${dialogDay}T00:00:00`) : null;
  const todayKey = dateKey(new Date());
  const today = dailyResults.find((day) => day.key === todayKey);
  const hasDeals = dailyResults.some((day) => day.deals > 0);
  const positiveDays = dailyResults.filter((day) => day.net > 0).length;
  const bestDay = dailyResults.reduce<DailyResult | null>((best, day) => day.deals && (!best || day.net > best.net) ? day : best, null);
  const currency = history?.currency ?? "";
  const source = history?.simulated ? "SIMULATION" : "MT5 · READ ONLY";
  const chartEmptyMessage = !history
    ? error ? "Performance data could not be loaded." : "Loading broker performance…"
    : !history.connected
      ? "Connect a broker account to populate this chart."
      : "No closed trades in the available 30-day history.";

  return (
    <section className="dashboard-performance card">
      <header className="performance-header">
        <div>
          <div className="performance-title-row"><span className="performance-icon"><svg viewBox="0 0 20 20" aria-hidden="true"><path d="M3 15.5 7.5 11l3 2.5L17 6.5" /><path d="M12.5 6.5H17V11" /></svg></span><h2>Daily trade performance</h2></div>
          <p>Realized broker deal results · 30-day view</p>
        </div>
        <span className={`pill ${history?.simulated ? "simulation-pill" : "broker-pill"}`}>{history ? source : error ? "UNAVAILABLE" : "LOADING"}</span>
      </header>

      {error && <p className="error-text performance-error" role="alert">{error}</p>}

      <div className="performance-metrics">
        <div><span>Today&apos;s net P&amp;L</span><strong className={today && today.net < 0 ? "position-loss" : today && today.net > 0 ? "position-profit" : ""}>{history?.connected && hasDeals && today ? formatAmount(today.net, currency) : "—"}</strong></div>
        <div><span>Deals today</span><strong>{history?.connected && hasDeals ? today?.deals ?? 0 : "—"}</strong></div>
        <div><span>Positive days · 30d</span><strong>{history?.connected && hasDeals ? `${positiveDays} / ${dayCount}` : "—"}</strong></div>
        <div><span>Best day · 30d</span><strong className="position-profit">{history?.connected && bestDay ? formatAmount(bestDay.net, currency) : "—"}</strong></div>
      </div>

      <div className="performance-content">
        <PerformanceCalendar
          month={calendarMonth}
          dailyTotals={dailyTotals}
          connected={Boolean(history?.connected)}
          currency={currency}
          periodDays={history?.period_days ?? 30}
          selectedDay={selectedDay}
          onSelectDay={(key) => {
            setSelectedDay(key);
            setDialogDay(key);
          }}
          onChangeMonth={(offset) => {
            const nextMonth = new Date(calendarMonth.getFullYear(), calendarMonth.getMonth() + offset, 1);
            const today = new Date();
            today.setHours(0, 0, 0, 0);
            const historyStart = new Date(today);
            historyStart.setDate(historyStart.getDate() - (history?.period_days ?? 30) + 1);
            setCalendarMonth(nextMonth);
            setSelectedDay(dateKey(nextMonth < historyStart ? historyStart : nextMonth));
          }}
        />
        <div className="performance-charts">
          <article className="performance-chart-card">
            <div className="performance-chart-heading"><div><h3>Daily net P&amp;L</h3><p>Profit, commission, and swap · local date</p></div><span>{currency || "Account currency"}</span></div>
            <div className={`performance-chart-plot ${!hasDeals ? "is-empty" : ""}`}>
              <BarChart days={dailyResults} currency={currency} />
              {!hasDeals && <p className="performance-chart-empty">{chartEmptyMessage}</p>}
            </div>
          </article>
          <article className="performance-chart-card">
            <div className="performance-chart-heading"><div><h3>Cumulative P&amp;L</h3><p>Running net result · last 30 days</p></div><span>{currency || "Account currency"}</span></div>
            <div className={`performance-chart-plot ${!hasDeals ? "is-empty" : ""}`}>
              <CumulativeChart days={dailyResults} currency={currency} />
              {!hasDeals && <p className="performance-chart-empty">{chartEmptyMessage}</p>}
            </div>
          </article>
        </div>
      </div>
      <p className="performance-footnote">Calendar and charts use raw broker deals, including manual activity; results are not attributed to this app&apos;s strategies. Available broker history is limited to the last {history?.period_days ?? 30} days. Refreshes every 30 seconds.</p>
      <dialog
        ref={dayTradesDialogRef}
        className="performance-day-dialog"
        aria-labelledby="performance-day-dialog-title"
        onCancel={(event) => { event.preventDefault(); setDialogDay(null); }}
      >
        {dialogDay && dialogDate && (
          <>
            <header className="performance-day-dialog-header">
              <span className="performance-day-dialog-icon" aria-hidden="true">
                <svg viewBox="0 0 24 24"><rect x="3.5" y="5" width="17" height="15.5" rx="2.5" /><path d="M7.5 3.5v3M16.5 3.5v3M4 9.5h16M8 13h3M8 16h2" /></svg>
              </span>
              <div>
                <span className="system-eyebrow">Daily trade ledger</span>
                <h2 id="performance-day-dialog-title">{dialogDate.toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric", year: "numeric" })}</h2>
                <p>Every deal recorded for this day · local time</p>
              </div>
              <button className="modal-close" type="button" aria-label="Close trade details" onClick={() => setDialogDay(null)}>×</button>
            </header>
            <div className="performance-day-dialog-summary">
              <div><span>Deals</span><strong>{selectedDayDeals.length}</strong></div>
              <div><span>Net result</span><strong className={selectedDayNet < 0 ? "position-loss" : selectedDayNet > 0 ? "position-profit" : ""}>{formatAmount(selectedDayNet, currency)}</strong></div>
            </div>
            {selectedDayDeals.length === 0 ? (
              <div className="empty performance-day-dialog-empty">No trades were recorded for this day.</div>
            ) : (
              <ol className="performance-day-trade-list">
                {selectedDayDeals.map((deal, index) => (
                  <li className="performance-day-trade" key={`${deal.ticket}-${deal.time}`}>
                    <div className="performance-day-trade-heading">
                      <div>
                        <span className="performance-day-trade-index">TRADE {String(index + 1).padStart(2, "0")} · {deal.deal_type === "ENTRY" ? "ENTRY" : deal.deal_type === "EXIT" ? "EXIT" : "BROKER DEAL"}</span>
                        <h3>{deal.symbol || "Unknown instrument"}</h3>
                      </div>
                      <span className={`signal-direction ${deal.direction === "BUY" ? "buy-direction" : deal.direction === "SELL" ? "sell-direction" : ""}`}>{deal.direction}</span>
                    </div>
                    <time className="performance-day-trade-time" dateTime={deal.time}>{new Date(deal.time).toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit", second: "2-digit" })}</time>
                    <dl className="performance-day-trade-identifiers">
                      <div><dt>Deal ID</dt><dd>{deal.ticket}</dd></div>
                      <div><dt>Order ID</dt><dd>{deal.order || "—"}</dd></div>
                    </dl>
                    <dl className="performance-day-trade-metrics">
                      <div><dt>Volume</dt><dd>{deal.volume}</dd></div>
                      <div><dt>Price</dt><dd>{deal.price}</dd></div>
                      <div><dt>Profit</dt><dd>{formatDealAmount(deal.profit, currency)}</dd></div>
                      <div><dt>Commission</dt><dd>{formatDealAmount(deal.commission, currency)}</dd></div>
                      <div><dt>Swap</dt><dd>{formatDealAmount(deal.swap, currency)}</dd></div>
                      <div className="performance-day-trade-net"><dt>Net result</dt><dd className={Number(deal.net_profit) < 0 ? "position-loss" : Number(deal.net_profit) > 0 ? "position-profit" : ""}>{formatDealAmount(deal.net_profit, currency)}</dd></div>
                    </dl>
                  </li>
                ))}
              </ol>
            )}
          </>
        )}
      </dialog>
    </section>
  );
}
