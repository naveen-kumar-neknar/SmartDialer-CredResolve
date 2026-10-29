import React from "react";
import {
  Users,
  UserCheck,
  PhoneCall,
  CheckCircle2,
  XCircle,
  Percent,
} from "lucide-react";

export default function MetricCards({ stats }) {
  const cards = [
    {
      title: "Available Agents",
      value: stats?.available_agents ?? 0,
      subtext: `Out of ${stats?.total_agents ?? 0} registered agents`,
      icon: UserCheck,
      iconBg: "rgba(22, 163, 74, 0.12)",
      iconColor: "#16a34a",
    },
    {
      title: "Active In-Flight Calls",
      value: stats?.active_calls ?? 0,
      subtext: `${stats?.reserved_agents ?? 0} agent(s) currently reserved`,
      icon: PhoneCall,
      iconBg: "rgba(2, 132, 199, 0.12)",
      iconColor: "#0284c7",
    },
    {
      title: "Completed Calls",
      value: stats?.completed_calls ?? 0,
      subtext: "Successfully wrapped sessions",
      icon: CheckCircle2,
      iconBg: "rgba(15, 23, 42, 0.08)",
      iconColor: "#0f172a",
    },
    {
      title: "Failed / Dropped Calls",
      value: stats?.failed_calls ?? 0,
      subtext: "Carrier failure, busy, or rejected",
      icon: XCircle,
      iconBg: "rgba(220, 38, 38, 0.12)",
      iconColor: "#dc2626",
    },
    {
      title: "Agent Fleet Utilization",
      value: `${stats?.agent_utilization_rate ?? 0}%`,
      subtext: "Active in-call vs ready capacity",
      icon: Percent,
      iconBg: "rgba(124, 58, 237, 0.12)",
      iconColor: "#7c3aed",
    },
    {
      title: "Call Connection Rate",
      value: `${stats?.call_connection_rate ?? 0}%`,
      subtext: "Completed / Total resolved calls",
      icon: Users,
      iconBg: "rgba(217, 119, 6, 0.12)",
      iconColor: "#d97706",
    },
  ];

  return (
    <div className="metrics-grid">
      {cards.map((c, i) => {
        const Icon = c.icon;
        return (
          <div key={i} className="metric-card">
            <div className="metric-header">
              <span>{c.title}</span>
              <div
                className="metric-icon"
                style={{ backgroundColor: c.iconBg, color: c.iconColor }}
              >
                <Icon size={18} />
              </div>
            </div>
            <div className="metric-value">{c.value}</div>
            <div className="metric-subtext">{c.subtext}</div>
          </div>
        );
      })}
    </div>
  );
}
