import React from "react";
import { ShieldAlert, CheckCircle, AlertTriangle, XCircle, ArrowRight } from "lucide-react";

export default function SafetyDecisionsTable({ decisions }) {
  const getVerdictBadge = (decision) => {
    switch (decision) {
      case "APPROVED":
        return <span className="badge badge-completed"><CheckCircle size={12} />APPROVED</span>;
      case "REDUCED":
        return <span className="badge badge-paused"><AlertTriangle size={12} />REDUCED</span>;
      case "FALLBACK_PROGRESSIVE":
        return <span className="badge badge-dialing"><ArrowRight size={12} />FALLBACK</span>;
      case "REJECTED":
        return <span className="badge badge-failed"><XCircle size={12} />HALTED</span>;
      default:
        return <span className="badge badge-offline">{decision}</span>;
    }
  };

  return (
    <div className="panel">
      <div className="panel-header">
        <div className="panel-title">
          <ShieldAlert size={18} color="var(--accent-primary)" />
          <span>Safety Controller Authorization Log</span>
          <span className="nav-badge">{decisions.length} recorded</span>
        </div>
      </div>

      <div className="table-responsive">
        <table>
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Mode</th>
              <th>Proposed &rarr; Approved</th>
              <th>Verdict</th>
              <th>Safety Rule Enforced</th>
              <th>Justification & Rationale</th>
            </tr>
          </thead>
          <tbody>
            {decisions.length === 0 ? (
              <tr>
                <td colSpan={6} style={{ textAlign: "center", color: "var(--text-muted)", padding: "32px" }}>
                  No safety evaluations recorded yet. Run a dialing batch or predictive simulation above.
                </td>
              </tr>
            ) : (
              decisions.map((d) => (
                <tr key={d.id}>
                  <td style={{ fontSize: "0.78rem", color: "var(--text-muted)", whiteSpace: "nowrap" }}>
                    {new Date(d.timestamp).toLocaleTimeString()}
                  </td>
                  <td>
                    <span className="badge badge-offline">
                      {d.dialer_mode}
                    </span>
                  </td>
                  <td>
                    <div style={{ display: "flex", alignItems: "center", gap: "6px", fontFamily: "var(--font-mono)", fontWeight: 600 }}>
                      <span style={{ color: "var(--text-muted)" }}>{d.engine_proposed_calls}</span>
                      <span style={{ color: "var(--text-muted)" }}>&rarr;</span>
                      <span style={{ color: d.approved_calls > 0 ? "var(--accent-emerald)" : "var(--accent-rose)" }}>
                        {d.approved_calls}
                      </span>
                    </div>
                  </td>
                  <td>{getVerdictBadge(d.decision)}</td>
                  <td>
                    <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.78rem", color: "var(--accent-cyan)" }}>
                      {d.rule_triggered}
                    </span>
                  </td>
                  <td style={{ fontSize: "0.82rem", color: "var(--text-secondary)", maxWidth: "420px" }}>
                    {d.reason}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
