import React from "react";
import { RefreshCw, Database, RotateCcw, Activity } from "lucide-react";

export default function Header({
  activeTab,
  stats,
  loading,
  onRefresh,
  onSeedDemo,
  onRunRecovery,
  currentUser,
  onLogout,
}) {
  const titles = {
    overview: {
      title: "Telephony Command Center",
      subtitle: "Live monitoring of agent allocation, progressive pacing, and safety controls.",
    },
    dialer: {
      title: "Progressive Dialer & Predictive Engine",
      subtitle: "Execute safe 1:1 progressive batches and simulate mathematical pacing proposals.",
    },
    calls: {
      title: "Call Session Management",
      subtitle: "Full audit lifecycle with strict state machine validation and event simulation.",
    },
    agents: {
      title: "Agent Fleet & Allocation",
      subtitle: "Manage agent availability, review assignments, and test concurrency locks.",
    },
    borrowers: {
      title: "Priority Borrower Queue",
      subtitle: "Masked customer data queue ordered by tier priority with zero real PII.",
    },
    safety: {
      title: "Safety Controller Audit Log",
      subtitle: "Autonomous rule-based validation records preventing overdialing and call dropouts.",
    },
    telecom: {
      title: "Telecom Provider Simulator",
      subtitle: "Interchangeable gateway emulation for Provider A (98% reliability) and Provider B (failure chaos).",
    },
  };

  const current = titles[activeTab] || titles.overview;

  return (
    <header className="header">
      <div className="header-left">
        <h2>{current.title}</h2>
        <p>{current.subtitle}</p>
      </div>

      <div className="header-actions">
        {/* Provider health badge */}
        <div
          className={`badge ${
            stats?.provider_health === "HEALTHY"
              ? "badge-available"
              : stats?.provider_health === "DEGRADED"
              ? "badge-paused"
              : "badge-failed"
          }`}
          style={{ padding: "6px 12px" }}
        >
          <Activity size={14} />
          <span>{stats?.active_provider || "ProviderA"}: {stats?.provider_health || "UNKNOWN"}</span>
        </div>

        <button
          className="btn btn-secondary btn-sm"
          onClick={onSeedDemo}
          disabled={loading}
          title="Seed 6 fictional agents and 25 fictional borrowers with zero real PII"
        >
          <Database size={15} />
          <span>Seed Demo Data</span>
        </button>

        <button
          className="btn btn-secondary btn-sm"
          onClick={onRunRecovery}
          disabled={loading}
          title="Reclaim stale reservations stuck due to network/worker timeout"
        >
          <RotateCcw size={15} />
          <span>Recover Stale</span>
        </button>

        <button
          className="btn btn-secondary btn-sm"
          onClick={onRefresh}
          disabled={loading}
        >
          <RefreshCw size={15} className={loading ? "spin" : ""} />
          <span>Refresh</span>
        </button>
      </div>
    </header>
  );
}
