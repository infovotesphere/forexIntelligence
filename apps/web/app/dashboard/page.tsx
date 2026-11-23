import { Page } from "@/components/Page";
import { ConnectionControls } from "@/components/ConnectionControls";

const metrics = [
  ["Account balance", "—"], ["Account equity", "—"], ["Free margin", "—"], ["Floating P/L", "—"],
  ["Today", "—"], ["This week", "—"], ["This month", "—"], ["Win rate", "—"],
];

export default function Dashboard() {
  return (
    <Page title="Trading overview" description="Live account and trading performance" active="/dashboard">
      <div style={{ marginBottom: 12 }}><ConnectionControls /></div>
      <section className="grid metrics">
        {metrics.map(([label, value]) => <div className="card metric" key={label}><div className="metric-label">{label}</div><div className="metric-value">{value}</div></div>)}
      </section>
      <section className="grid two-col">
        <div className="card panel"><h2>Equity curve</h2><div className="empty">No account history</div></div>
        <div className="card panel"><h2>Risk utilisation</h2><div className="empty">No open risk</div></div>
      </section>
      <section className="grid two-col">
        <div className="card panel"><h2>Recent trades</h2><div className="empty">No closed trades</div></div>
        <div className="card panel"><h2>Recent signals</h2><div className="empty">No signals generated</div></div>
      </section>
    </Page>
  );
}
