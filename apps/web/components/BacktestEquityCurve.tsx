export type BacktestEquityPoint = {
  trade_number: number;
  time: string;
  cumulative_r: string;
  drawdown_r: string;
};

type Props = {
  points: BacktestEquityPoint[];
};

const chartWidth = 720;
const chartHeight = 220;
const chartPadding = { top: 18, right: 46, bottom: 20, left: 16 };

function formatTime(value: string): string {
  return new Date(value).toLocaleString();
}

function formatR(value: string): string {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? `${parsed.toFixed(2)}R` : "—";
}

export function BacktestEquityCurve({ points }: Props) {
  if (points.length === 0) {
    return (
      <section className="card equity-panel">
        <div className="equity-heading">
          <div><h2>Realized equity curve</h2><p>Cumulative result from closed trades, measured in R</p></div>
        </div>
        <div className="empty equity-empty">The curve appears after the replay has a closed trade.</div>
      </section>
    );
  }

  const values = points.map((point) => Number(point.cumulative_r));
  const rawMin = Math.min(0, ...values);
  const rawMax = Math.max(0, ...values);
  const padding = Math.max((rawMax - rawMin) * 0.12, 0.5);
  const minValue = rawMin - padding;
  const maxValue = rawMax + padding;
  const plotWidth = chartWidth - chartPadding.left - chartPadding.right;
  const plotHeight = chartHeight - chartPadding.top - chartPadding.bottom;
  const yFor = (value: number) => chartPadding.top + (maxValue - value) / (maxValue - minValue) * plotHeight;
  const plottedPoints = points.map((point, index) => ({
    ...point,
    x: chartPadding.left + plotWidth * index / Math.max(values.length - 1, 1),
    y: yFor(values[index]),
  }));
  const coordinates = plottedPoints.map((point) => `${point.x},${point.y}`);
  const zeroY = yFor(0);
  const firstPoint = points[0];
  const lastPoint = points[points.length - 1];

  return (
    <section className="card equity-panel">
      <div className="equity-heading">
        <div><h2>Realized equity curve</h2><p>{points.length} closed trades · cumulative result in R</p></div>
        <span className="equity-current">{formatR(lastPoint.cumulative_r)}</span>
      </div>
      <div className="equity-chart">
        <svg viewBox={`0 0 ${chartWidth} ${chartHeight}`} preserveAspectRatio="none" role="img" aria-label="Cumulative R result after each closed backtest trade">
          <line className="equity-gridline" x1={chartPadding.left} x2={chartWidth - chartPadding.right} y1={chartPadding.top} y2={chartPadding.top} />
          <line className="equity-zero-line" x1={chartPadding.left} x2={chartWidth - chartPadding.right} y1={zeroY} y2={zeroY} />
          <line className="equity-gridline" x1={chartPadding.left} x2={chartWidth - chartPadding.right} y1={chartHeight - chartPadding.bottom} y2={chartHeight - chartPadding.bottom} />
          <text className="equity-axis-label" x={chartWidth - chartPadding.right + 8} y={zeroY + 4}>0R</text>
          <polygon
            className="equity-area"
            points={`${chartPadding.left},${zeroY} ${coordinates.join(" ")} ${chartWidth - chartPadding.right},${zeroY}`}
          />
          <polyline className="equity-line" points={coordinates.join(" ")} />
          {plottedPoints.map((point, index) => (
            <circle
              className={index === plottedPoints.length - 1 ? "equity-last-point" : "equity-point"}
              cx={point.x}
              cy={point.y}
              key={point.trade_number}
              r={index === plottedPoints.length - 1 ? "4" : "2"}
            >
              <title>{`Trade ${point.trade_number} · cumulative ${formatR(point.cumulative_r)} · drawdown ${formatR(point.drawdown_r)}`}</title>
            </circle>
          ))}
        </svg>
      </div>
      <div className="equity-axis-labels"><span>First close · {formatTime(firstPoint.time)}</span><span>Latest close · {formatTime(lastPoint.time)}</span></div>
    </section>
  );
}
