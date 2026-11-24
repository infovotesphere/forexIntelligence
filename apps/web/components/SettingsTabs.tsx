"use client";

import { type KeyboardEvent, useEffect, useRef, useState } from "react";
import { AccountSettings } from "./AccountSettings";
import { ConnectionControls } from "./ConnectionControls";
import { MT5ConnectionForm } from "./MT5ConnectionForm";
import { UserManagement } from "./UserManagement";

const tabs = [
  { id: "account", label: "Account", icon: "account" },
  { id: "broker", label: "Broker connection", icon: "broker" },
  { id: "mt5", label: "MT5 connection", icon: "terminal" },
  { id: "users", label: "Users", icon: "users" },
] as const;

type SettingsTab = typeof tabs[number]["id"];
type TabIconName = typeof tabs[number]["icon"];

function SettingsTabIcon({ name }: { name: TabIconName }) {
  return (
    <svg className="settings-tab-icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {name === "account" && <><circle cx="10" cy="6.5" r="3" /><path d="M4 17a6 6 0 0 1 12 0" /></>}
      {name === "broker" && <><path d="M7.5 12.5 6 14a3 3 0 0 1-4-4l3-3a3 3 0 0 1 4.3 0" /><path d="m12.5 7.5 1.5-1.5a3 3 0 0 1 4 4l-3 3a3 3 0 0 1-4.3 0M6.5 10h7" /></>}
      {name === "terminal" && <><rect x="2.5" y="3" width="15" height="14" rx="2" /><path d="M5.5 13.5 8 10l2.2 1.8 4.3-5" /></>}
      {name === "users" && <><circle cx="7.5" cy="7" r="2.5" /><path d="M2 16a5.5 5.5 0 0 1 11 0M13 5a2.5 2.5 0 0 1 0 5m2 2a4 4 0 0 1 3 4" /></>}
    </svg>
  );
}

export function SettingsTabs() {
  const [activeTab, setActiveTab] = useState<SettingsTab>("account");
  const [isAdministrator, setIsAdministrator] = useState(false);
  const tabRefs = useRef<Array<HTMLButtonElement | null>>([]);
  const visibleTabs = isAdministrator ? tabs : tabs.filter((tab) => tab.id !== "users");

  useEffect(() => {
    fetch("/api/v1/auth/profile", { cache: "no-store" })
      .then(async (response) => {
        if (!response.ok) return;
        const profile = await response.json() as { role: string };
        setIsAdministrator(profile.role === "administrator");
      })
      .catch(() => setIsAdministrator(false));
  }, []);

  function handleTabKeyDown(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    let nextIndex: number;
    if (event.key === "ArrowRight") {
      nextIndex = (index + 1) % visibleTabs.length;
    } else if (event.key === "ArrowLeft") {
      nextIndex = (index - 1 + visibleTabs.length) % visibleTabs.length;
    } else if (event.key === "Home") {
      nextIndex = 0;
    } else if (event.key === "End") {
      nextIndex = visibleTabs.length - 1;
    } else {
      return;
    }

    event.preventDefault();
    setActiveTab(visibleTabs[nextIndex].id);
    tabRefs.current[nextIndex]?.focus();
  }

  return (
    <div className="settings-tabs">
      <div className="settings-tab-list" role="tablist" aria-label="Settings sections">
        {visibleTabs.map((tab, index) => (
          <button
            key={tab.id}
            ref={(element) => { tabRefs.current[index] = element; }}
            id={`settings-tab-${tab.id}`}
            className="settings-tab"
            type="button"
            role="tab"
            aria-selected={activeTab === tab.id}
            aria-controls="settings-tab-panel"
            tabIndex={activeTab === tab.id ? 0 : -1}
            onClick={() => setActiveTab(tab.id)}
            onKeyDown={(event) => handleTabKeyDown(event, index)}
          >
            <SettingsTabIcon name={tab.icon} />
            {tab.label}
          </button>
        ))}
      </div>
      <div
        className="settings-tab-panel"
        id="settings-tab-panel"
        role="tabpanel"
        aria-labelledby={`settings-tab-${activeTab}`}
        tabIndex={0}
      >
        {activeTab === "account" && <AccountSettings />}
        {activeTab === "broker" && <ConnectionControls />}
        {activeTab === "users" && isAdministrator && <UserManagement />}
        {activeTab === "mt5" && (
          <>
            <MT5ConnectionForm />
            <section className="card panel">
              <h2>MT5 Windows connection</h2>
              <p className="safety-note">You can manage this connection from an iPad or any browser. MT5 credentials wait for the authenticated worker running on a Windows computer or VPS with the MT5 desktop terminal installed; an iPad cannot run that worker. Keep the Windows terminal and worker online to connect and report account status.</p>
              <div className="button-row">
                <span className="pill">Live trading: disabled</span>
                <span className="pill">Demo environment: required</span>
              </div>
            </section>
          </>
        )}
      </div>
    </div>
  );
}
