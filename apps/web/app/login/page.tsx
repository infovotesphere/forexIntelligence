export default function Login() {
  return (
    <main style={{ minHeight: "100vh", display: "grid", placeItems: "center", background: "#080d14" }}>
      <div className="card" style={{ width: 360, maxWidth: "calc(100vw - 32px)", padding: 24 }}>
        <div className="brand" style={{ marginBottom: 12 }}><span className="brand-mark">FI</span><span>Forex Intelligence</span></div>
        <h1 style={{ fontSize: 20, margin: "8px 0" }}>Sign in</h1>
        <p style={{ color: "#8fa1b3", fontSize: 13 }}>Authentication provisioning is part of the next implementation milestone.</p>
      </div>
    </main>
  );
}
