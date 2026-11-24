import type { ReactNode } from "react";

export function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <main className="auth-screen">
      <div className="auth-layout">
        <aside className="auth-aside">
          <div className="auth-brand">
            <span className="brand-mark">FI</span>
            <span>Forex Intelligence</span>
          </div>
          <div className="auth-hero">
            <span className="auth-eyebrow">TRADING INTELLIGENCE</span>
            <h2>A clearer view of your trading workspace.</h2>
            <p>Bring market context, trade history, and strategy research together in one focused place.</p>
            <ul className="auth-feature-list">
              <li><i />Market-aware analysis</li>
              <li><i />Read-only broker visibility</li>
              <li><i />Built for desktop and mobile</li>
            </ul>
          </div>
          <div className="auth-art" aria-hidden="true">
            <svg viewBox="0 0 560 210" preserveAspectRatio="none">
              <defs>
                <linearGradient id="auth-chart-fill" x1="0" x2="0" y1="0" y2="1">
                  <stop offset="0" stopColor="#52c9a5" stopOpacity=".2" />
                  <stop offset="1" stopColor="#52c9a5" stopOpacity="0" />
                </linearGradient>
              </defs>
              <path className="auth-chart-grid" d="M0 35h560M0 85h560M0 135h560M0 185h560M70 0v210M170 0v210M270 0v210M370 0v210M470 0v210" />
              <path className="auth-chart-area" d="M0 160 55 146 95 158 145 116 190 130 240 88 290 107 340 66 390 88 445 45 495 67 560 25V210H0Z" />
              <path className="auth-chart-line" d="M0 160 55 146 95 158 145 116 190 130 240 88 290 107 340 66 390 88 445 45 495 67 560 25" />
              <circle className="auth-chart-point" cx="445" cy="45" r="4" />
              <circle className="auth-chart-point" cx="560" cy="25" r="4" />
            </svg>
            <span>MARKET CONTEXT · STRATEGY RESEARCH · TRADE HISTORY</span>
          </div>
          <span className="auth-aside-footer">Forex Intelligence <i /> A focused trading workspace</span>
        </aside>
        <div className="auth-form-area">
          <div className="auth-mobile-brand">
            <span className="brand-mark">FI</span>
            <strong>Forex Intelligence</strong>
          </div>
          {children}
        </div>
      </div>
    </main>
  );
}
