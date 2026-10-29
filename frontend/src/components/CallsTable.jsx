import React, { useState } from "react";
import { Phone, CheckCircle, XCircle, Clock, Eye, Info } from "lucide-react";

export default function CallsTable({ calls, onSimulateCall, onViewDetails }) {
  const [filter, setFilter] = useState("ALL");

  const filteredCalls = filter === "ALL"
    ? calls
    : calls.filter((c) => c.status === filter);

  const getStatusBadge = (status) => {
    switch (status) {
      case "AVAILABLE":
      case "COMPLETED":
        return <span className="badge badge-completed"><span className="badge-dot" style={{ background: "#10b981" }} />{status}</span>;
      case "CONNECTED":
        return <span className="badge badge-connected"><span className="badge-dot" style={{ background: "#06b6d4" }} />{status}</span>;
      case "INITIATED":
      case "RINGING":
      case "ANSWERED":
        return <span className="badge badge-ringing"><span className="badge-dot" style={{ background: "#f59e0b" }} />{status}</span>;
      case "RESERVED":
        return <span className="badge badge-reserved"><span className="badge-dot" style={{ background: "#a855f7" }} />{status}</span>;
      case "FAILED":
      case "CANCELLED":
        return <span className="badge badge-failed"><span className="badge-dot" style={{ background: "#ef4444" }} />{status}</span>;
      default:
        return <span className="badge badge-offline">{status}</span>;
    }
  };

  return (
    <div className="panel">
      <div className="panel-header">
        <div className="panel-title">
          <Phone size={18} color="var(--accent-cyan)" />
          <span>Call Sessions Activity</span>
          <span className="nav-badge">{filteredCalls.length} calls</span>
        </div>

        <div className="panel-actions">
          <select
            className="form-select"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            style={{ padding: "5px 10px", fontSize: "0.8rem" }}
          >
            <option value="ALL">All States</option>
            <option value="INITIATED">INITIATED</option>
            <option value="RINGING">RINGING</option>
            <option value="CONNECTED">CONNECTED</option>
            <option value="COMPLETED">COMPLETED</option>
            <option value="FAILED">FAILED</option>
          </select>
        </div>
      </div>

      <div className="table-responsive">
        {filteredCalls.length === 0 ? (
          <div className="empty-state">
            <Info size={32} className="empty-icon" />
            <p>No call sessions match the selected criteria.</p>
          </div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Call ID</th>
                <th>Borrower</th>
                <th>Agent</th>
                <th>Gateway</th>
                <th>Status</th>
                <th>Duration</th>
                <th>Initiated At</th>
                <th>Simulate Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredCalls.map((call) => {
                const isActive = ["INITIATED", "RINGING", "ANSWERED", "RESERVED"].includes(call.status);
                const isConnected = call.status === "CONNECTED";
                const isTerminal = ["COMPLETED", "FAILED", "CANCELLED"].includes(call.status);

                return (
                  <tr key={call.id}>
                    <td style={{ fontFamily: "var(--font-mono)", fontWeight: 600 }}>
                      #{call.id}
                    </td>
                    <td>Borrower #{call.borrower_id}</td>
                    <td>
                      {call.agent_id ? (
                        <span style={{ color: "var(--accent-cyan)" }}>Agent #{call.agent_id}</span>
                      ) : (
                        <span style={{ color: "var(--text-muted)" }}>None (Unallocated)</span>
                      )}
                    </td>
                    <td>
                      <span className="badge badge-offline">
                        {call.provider || "ProviderA"}
                      </span>
                    </td>
                    <td>{getStatusBadge(call.status)}</td>
                    <td>
                      <div style={{ display: "flex", alignItems: "center", gap: "4px", color: "var(--text-muted)" }}>
                        <Clock size={13} />
                        <span>{call.duration_seconds || 0}s</span>
                      </div>
                    </td>
                    <td style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}>
                      {call.initiated_at ? new Date(call.initiated_at).toLocaleTimeString() : "-"}
                    </td>
                    <td>
                      <div style={{ display: "flex", gap: "6px" }}>
                        {isActive && (
                          <>
                            <button
                              className="btn btn-secondary btn-sm"
                              style={{ color: "#34d399", borderColor: "rgba(16, 185, 129, 0.3)" }}
                              onClick={() => onSimulateCall(call.id, "CONNECTED")}
                              title="Advance state machine: Borrower answers and connects to agent"
                            >
                              <CheckCircle size={13} />
                              <span>Connect</span>
                            </button>
                            <button
                              className="btn btn-danger btn-sm"
                              onClick={() => onSimulateCall(call.id, "FAILED", "User Busy / No Answer")}
                              title="Advance state machine: Call fails or line busy"
                            >
                              <XCircle size={13} />
                              <span>Fail</span>
                            </button>
                          </>
                        )}

                        {isConnected && (
                          <button
                            className="btn btn-secondary btn-sm"
                            style={{ color: "#818cf8", borderColor: "rgba(99, 102, 241, 0.3)" }}
                            onClick={() => onSimulateCall(call.id, "COMPLETED")}
                            title="Wrap up call session and free up agent"
                          >
                            <CheckCircle size={13} />
                            <span>Complete</span>
                          </button>
                        )}

                        {isTerminal && (
                          <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                            Terminal State &bull; Immutable
                          </span>
                        )}

                        <button
                          className="btn btn-secondary btn-sm"
                          onClick={() => onViewDetails(call.id)}
                          title="View Call Inspection Record"
                        >
                          <Eye size={13} />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
