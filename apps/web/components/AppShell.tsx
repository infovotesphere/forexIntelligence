import Link from "next/link";
import { LogoutButton } from "./LogoutButton";
import { StatusBar } from "./StatusBar";

const nav = [
  ["Overview", "/dashboard", "⌂"], ["Markets", "/markets", "◫"],
  ["Signals", "/signals", "⌁"], ["Positions", "/positions", "▣"],
  ["Orders", "/orders", "≡"], ["History", "/history", "◷"],
  ["Analytics", "/analytics", "⌗"], ["Strategies", "/strategies", "◆"],
  ["Risk", "/risk", "◉"], ["Backtesting", "/backtesting", "⟳"],
  ["Notifications", "/notifications", "↗"], ["Settings", "/settings", "⚙"],
];

export function AppShell({ children, active = "/dashboard" }: { children: React.ReactNode; active?: string }) {
  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand"><span className="brand-mark">FI</span><span className="brand-name">Forex Intelligence</span></div>
        <nav className="nav" aria-label="Primary navigation">
          {nav.map(([label, href, icon]) => (
            <Link key={href} href={href} className={active === href ? "active" : ""} title={label}>
              <span className="nav-icon">{icon}</span><span className="nav-label">{label}</span>
            </Link>
          ))}
        </nav>
      </aside>
      <div className="main">
        <header className="topbar">
          <StatusBar />
          <LogoutButton />
        </header>
        {children}
      </div>
    </div>
  );
}
