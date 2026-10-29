import React from "react";
import {
  LayoutDashboard,
  PhoneCall,
  Users,
  UserCheck,
  ShieldAlert,
  Radio,
  Sliders,
  LogOut,
} from "lucide-react";

export default function Sidebar({ activeTab, setActiveTab, stats, currentUser, onLogout }) {
  const navItems = [
    { id: "overview", label: "Overview", icon: LayoutDashboard },
    { id: "dialer", label: "Dialer & Pacing", icon: Sliders },
    {
      id: "calls",
      label: "Call Log",
      icon: PhoneCall,
      badge: stats?.active_calls ? `${stats.active_calls} active` : null,
      badgeColor: "var(--accent-cyan)",
    },
    {
      id: "agents",
      label: "Agents",
      icon: UserCheck,
      badge: stats?.available_agents ? `${stats.available_agents} ready` : null,
      badgeColor: "var(--accent-emerald)",
    },
    { id: "borrowers", label: "Borrower Queue", icon: Users },
    { id: "safety", label: "Safety Controller", icon: ShieldAlert },
    { id: "telecom", label: "Telecom Providers", icon: Radio },
  ];

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="logo-icon">
          <PhoneCall size={20} />
        </div>
        <div className="logo-text">
          <h1>SmartDialer</h1>
          <span>Telephony Ops</span>
        </div>
      </div>

      <nav className="sidebar-nav">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              className={`nav-item ${isActive ? "active" : ""}`}
              onClick={() => setActiveTab(item.id)}
            >
              <Icon size={18} />
              <span>{item.label}</span>
              {item.badge && (
                <span
                  className="nav-badge"
                  style={{ color: item.badgeColor }}
                >
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      <div className="sidebar-footer">
        {currentUser && (
          <div style={{ display: "flex", flexDirection: "column", gap: "8px", width: "100%", paddingBottom: "12px", borderBottom: "1px solid var(--border-color)", marginBottom: "12px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <div style={{ width: "32px", height: "32px", borderRadius: "50%", backgroundColor: "#0f172a", color: "#ffffff", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "12px", fontWeight: "700" }}>
                {currentUser.name ? currentUser.name.charAt(0) : "U"}
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: "13px", fontWeight: "600", color: "var(--text-primary)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {currentUser.name}
                </div>
                <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                  {currentUser.role || "Operator"}
                </div>
              </div>
            </div>
            <button
              onClick={onLogout}
              className="btn btn-secondary btn-sm"
              style={{ width: "100%", justifyContent: "center", gap: "6px", fontSize: "12px", padding: "6px" }}
              title="Sign out of SmartDialer session"
            >
              <LogOut size={13} />
              <span>Sign Out</span>
            </button>
          </div>
        )}
        <div style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "12px" }}>
          <div
            style={{
              width: "8px",
              height: "8px",
              borderRadius: "50%",
              backgroundColor: stats?.provider_health === "HEALTHY" ? "var(--accent-emerald)" : "var(--accent-rose)",
            }}
          />
          <span style={{ fontWeight: 500, color: "var(--text-secondary)" }}>
            Telephony Gateway: {stats?.active_provider || "ProviderA"}
          </span>
        </div>
      </div>
    </aside>
  );
}
