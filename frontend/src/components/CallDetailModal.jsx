import React from "react";
import { PhoneCall, Clock, ShieldCheck, UserCheck, AlertCircle } from "lucide-react";

export default function CallDetailModal({ call, onClose }) {
  if (!call) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <PhoneCall size={18} color="var(--accent-cyan)" />
            <h3 style={{ fontSize: "1.1rem", fontWeight: 600 }}>
              Call Session #{call.id}
            </h3>
          </div>
          <button className="btn btn-secondary btn-sm" onClick={onClose}>
            &times;
          </button>
        </div>

        <div className="modal-body">
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
            <div style={{ background: "#f8fafc", padding: "12px", borderRadius: "8px", border: "1px solid var(--border-color)" }}>
              <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Current Status</div>
              <div style={{ fontSize: "1.1rem", fontWeight: 700, color: "var(--text-primary)", marginTop: "2px" }}>
                {call.status}
              </div>
            </div>

            <div style={{ background: "#f8fafc", padding: "12px", borderRadius: "8px", border: "1px solid var(--border-color)" }}>
              <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Talk Duration</div>
              <div style={{ fontSize: "1.1rem", fontWeight: 700, color: "var(--text-primary)", marginTop: "2px" }}>
                {call.duration_seconds || 0} seconds
              </div>
            </div>
          </div>

          {/* Borrower Card */}
          <div style={{ background: "#ffffff", padding: "14px", borderRadius: "8px", border: "1px solid var(--border-color)" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px", fontWeight: 600, fontSize: "0.88rem", marginBottom: "8px", color: "var(--text-primary)" }}>
              <ShieldCheck size={16} color="var(--accent-emerald)" />
              <span>Borrower Information</span>
            </div>
            {call.borrower ? (
              <div style={{ fontSize: "0.82rem", display: "flex", flexDirection: "column", gap: "4px" }}>
                <div>Name: <strong>{call.borrower.name}</strong></div>
                <div>Contact: <span style={{ fontFamily: "var(--font-mono)" }}>{call.borrower.phone_number}</span> (Masked)</div>
                <div>Priority: Tier {call.borrower.priority}</div>
              </div>
            ) : (
              <div style={{ fontSize: "0.82rem", color: "var(--text-muted)" }}>
                Borrower ID #{call.borrower_id}
              </div>
            )}
          </div>

          {/* Agent Card */}
          <div style={{ background: "#ffffff", padding: "14px", borderRadius: "8px", border: "1px solid var(--border-color)" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px", fontWeight: 600, fontSize: "0.88rem", marginBottom: "8px", color: "var(--text-primary)" }}>
              <UserCheck size={16} color="var(--accent-cyan)" />
              <span>Allocated Agent</span>
            </div>
            {call.agent ? (
              <div style={{ fontSize: "0.82rem", display: "flex", flexDirection: "column", gap: "4px" }}>
                <div>Name: <strong>{call.agent.name}</strong></div>
                <div>Status: <span className="badge badge-available">{call.agent.status}</span></div>
              </div>
            ) : (
              <div style={{ fontSize: "0.82rem", color: "var(--text-muted)" }}>
                {call.agent_id ? `Agent ID #${call.agent_id}` : "No Agent Allocated"}
              </div>
            )}
          </div>

          {/* Telephony Metadata */}
          <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", display: "flex", flexDirection: "column", gap: "4px" }}>
            <div>Gateway: <strong>{call.provider}</strong></div>
            <div>Gateway Call Reference: <span style={{ fontFamily: "var(--font-mono)" }}>{call.provider_call_id || "Pending"}</span></div>
            <div>Initiated: {call.initiated_at ? new Date(call.initiated_at).toLocaleString() : "-"}</div>
            <div>Connected: {call.connected_at ? new Date(call.connected_at).toLocaleString() : "-"}</div>
            <div>Ended: {call.ended_at ? new Date(call.ended_at).toLocaleString() : "-"}</div>
            {call.failure_reason && (
              <div style={{ color: "var(--accent-rose)", display: "flex", gap: "6px", marginTop: "4px" }}>
                <AlertCircle size={15} />
                <span>Failure Reason: {call.failure_reason}</span>
              </div>
            )}
          </div>
        </div>

        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
