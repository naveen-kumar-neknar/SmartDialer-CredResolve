import React from "react";
import { UserCheck, Shield, PhoneCall } from "lucide-react";

export default function AgentsTable({ agents, onStatusChange }) {
  const getStatusBadge = (status) => {
    switch (status) {
      case "AVAILABLE":
        return <span className="badge badge-available"><span className="badge-dot" style={{ background: "#10b981" }} />AVAILABLE</span>;
      case "CONNECTED":
        return <span className="badge badge-connected"><span className="badge-dot" style={{ background: "#06b6d4" }} />CONNECTED</span>;
      case "DIALING":
        return <span className="badge badge-dialing"><span className="badge-dot" style={{ background: "#f59e0b" }} />DIALING</span>;
      case "RESERVED":
        return <span className="badge badge-reserved"><span className="badge-dot" style={{ background: "#a855f7" }} />RESERVED</span>;
      case "WRAP_UP":
        return <span className="badge badge-wrap-up"><span className="badge-dot" style={{ background: "#6366f1" }} />WRAP_UP</span>;
      case "PAUSED":
        return <span className="badge badge-paused"><span className="badge-dot" style={{ background: "#f59e0b" }} />PAUSED</span>;
      default:
        return <span className="badge badge-offline"><span className="badge-dot" style={{ background: "#64748b" }} />OFFLINE</span>;
    }
  };

  return (
    <div className="panel">
      <div className="panel-header">
        <div className="panel-title">
          <UserCheck size={18} color="var(--accent-emerald)" />
          <span>Agent Fleet Status & Availability</span>
          <span className="nav-badge">{agents.length} agents</span>
        </div>
      </div>

      <div className="table-responsive">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Agent Name</th>
              <th>Current Status</th>
              <th>Active Call</th>
              <th>Reserved At</th>
              <th>Change Availability</th>
            </tr>
          </thead>
          <tbody>
            {agents.map((agent) => {
              const isLocked = ["RESERVED", "DIALING", "CONNECTED"].includes(agent.status);

              return (
                <tr key={agent.id}>
                  <td style={{ fontFamily: "var(--font-mono)", fontWeight: 600 }}>
                    #{agent.id}
                  </td>
                  <td style={{ fontWeight: 500 }}>{agent.name}</td>
                  <td>{getStatusBadge(agent.status)}</td>
                  <td>
                    {agent.current_call_id ? (
                      <div style={{ display: "flex", alignItems: "center", gap: "6px", color: "var(--accent-cyan)" }}>
                        <PhoneCall size={13} />
                        <span>Call #{agent.current_call_id}</span>
                      </div>
                    ) : (
                      <span style={{ color: "var(--text-muted)" }}>None (Idle)</span>
                    )}
                  </td>
                  <td style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}>
                    {agent.reserved_at ? new Date(agent.reserved_at).toLocaleTimeString() : "-"}
                  </td>
                  <td>
                    {isLocked ? (
                      <div style={{ display: "flex", alignItems: "center", gap: "6px", color: "var(--text-muted)", fontSize: "0.78rem" }}>
                        <Shield size={13} color="var(--accent-amber)" />
                        <span>Locked in Call</span>
                      </div>
                    ) : (
                      <select
                        className="form-select"
                        value={agent.status}
                        onChange={(e) => onStatusChange(agent.id, e.target.value)}
                        style={{ padding: "4px 8px", fontSize: "0.8rem", width: "130px" }}
                      >
                        <option value="AVAILABLE">AVAILABLE</option>
                        <option value="PAUSED">PAUSED</option>
                        <option value="OFFLINE">OFFLINE</option>
                      </select>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
