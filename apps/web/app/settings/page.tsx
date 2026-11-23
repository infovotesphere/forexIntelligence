import { Page } from "@/components/Page";
import { ConnectionControls } from "@/components/ConnectionControls";
import { MT5ConnectionForm } from "@/components/MT5ConnectionForm";
export default function Settings() {
  return (
    <Page title="Settings" description="Broker, account and system configuration" active="/settings">
      <ConnectionControls />
      <div style={{ marginTop: 12 }}><MT5ConnectionForm /></div>
      <section className="card panel" style={{ marginTop: 12 }}>
        <h2>MT5 Windows connection</h2>
        <p className="safety-note">Run the authenticated worker on the Windows computer where the MT5 desktop terminal is installed. It polls this backend for the encrypted demo login and reports connection/account status.</p>
        <div className="button-row">
          <span className="pill">Live trading: disabled</span>
          <span className="pill">Demo environment: required</span>
        </div>
      </section>
    </Page>
  );
}
