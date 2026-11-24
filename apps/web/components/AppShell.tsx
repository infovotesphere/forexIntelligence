import Link from "next/link";
import { LogoutButton } from "./LogoutButton";
import { StatusBar } from "./StatusBar";

type NavIconName =
  | "overview" | "markets" | "signals" | "positions" | "orders" | "history"
  | "analytics" | "strategies" | "risk" | "backtesting" | "notifications" | "system" | "settings";

type NavItem = { label: string; href: string; icon: NavIconName };

const navGroups: { label: string; items: NavItem[] }[] = [
  { label: "Workspace", items: [
    { label: "Overview", href: "/dashboard", icon: "overview" },
    { label: "Markets", href: "/markets", icon: "markets" },
    { label: "Signals", href: "/signals", icon: "signals" },
    { label: "Positions", href: "/positions", icon: "positions" },
    { label: "Orders", href: "/orders", icon: "orders" },
    { label: "History", href: "/history", icon: "history" },
  ] },
  { label: "Research", items: [
    { label: "Analytics", href: "/analytics", icon: "analytics" },
    { label: "Strategies", href: "/strategies", icon: "strategies" },
    { label: "Risk", href: "/risk", icon: "risk" },
    { label: "Backtesting", href: "/backtesting", icon: "backtesting" },
  ] },
  { label: "Platform", items: [
    { label: "Notifications", href: "/notifications", icon: "notifications" },
    { label: "System", href: "/system", icon: "system" },
    { label: "Settings", href: "/settings", icon: "settings" },
  ] },
];

function NavIcon({ name }: { name: NavIconName }) {
  let shape: React.ReactNode;
  switch (name) {
    case "overview":
      shape = <><path d="m3.5 10 8.5-7 8.5 7" /><path d="M5.5 9v11h13V9M9 20v-6h6v6" /></>;
      break;
    case "markets":
      shape = <><path d="M5 4v16M12 3v18M19 6v12" /><path d="M3 8h4M10 15h4M17 10h4" /></>;
      break;
    case "signals":
      shape = <><path d="M3 12h3l3-7 5 14 3-7h4" /><circle cx="9" cy="5" r="1" /></>;
      break;
    case "positions":
      shape = <><rect x="4" y="4" width="12" height="12" rx="2" /><path d="M8 20h9a3 3 0 0 0 3-3V8" /></>;
      break;
    case "orders":
      shape = <><path d="M8 6h12M8 12h12M8 18h12" /><circle cx="4" cy="6" r=".8" /><circle cx="4" cy="12" r=".8" /><circle cx="4" cy="18" r=".8" /></>;
      break;
    case "history":
      shape = <><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3.5 2" /></>;
      break;
    case "analytics":
      shape = <><path d="M4 19V9m5 10V5m5 14v-7m5 7V3" /><path d="M2 19h20" /></>;
      break;
    case "strategies":
      shape = <><path d="M5 5h5v5H5zM14 14h5v5h-5zM10 7.5h2a3 3 0 0 1 3 3V14" /><path d="M7.5 10v4a3 3 0 0 0 3 3H14" /></>;
      break;
    case "risk":
      shape = <><path d="M12 3 20 6v5c0 5-3.5 8-8 10-4.5-2-8-5-8-10V6z" /><path d="M12 8v5m0 3h.01" /></>;
      break;
    case "backtesting":
      shape = <><path d="M4 7V3m0 4h4" /><path d="M5.5 7a8 8 0 1 1-1 8" /><path d="M12 7v5l3 2" /></>;
      break;
    case "notifications":
      shape = <><path d="M18 9a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9" /><path d="M10 21h4" /></>;
      break;
    case "system":
      shape = <><rect x="3" y="4" width="18" height="6" rx="2" /><rect x="3" y="14" width="18" height="6" rx="2" /><path d="M7 7h.01M7 17h.01M11 7h6m-6 10h6" /></>;
      break;
    case "settings":
      shape = <><path d="M4 7h8m4 0h4M4 17h3m4 0h9" /><circle cx="14" cy="7" r="2" /><circle cx="9" cy="17" r="2" /></>;
      break;
  }
  return <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{shape}</svg>;
}

export function AppShell({ children, active = "/dashboard" }: { children: React.ReactNode; active?: string }) {
  return (
    <div className="shell">
      <aside className="sidebar">
        <Link href="/dashboard" className="brand" aria-label="Forex Intelligence overview">
          <span className="brand-mark">FI</span><span className="brand-name">Forex Intelligence</span>
        </Link>
        <nav className="nav" aria-label="Primary navigation">
          {navGroups.map((group) => (
            <div className="nav-group" key={group.label} role="group" aria-label={group.label}>
              <span className="nav-group-label">{group.label}</span>
              {group.items.map(({ label, href, icon }) => (
                <Link key={href} href={href} className={active === href ? "active" : ""} title={label} aria-label={label} aria-current={active === href ? "page" : undefined}>
                  <NavIcon name={icon} /><span className="nav-label">{label}</span>
                </Link>
              ))}
            </div>
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
