import React, { useState } from "react";
import { Users, Plus, ShieldCheck, Phone } from "lucide-react";

export default function BorrowersTable({ borrowers, onAddBorrower }) {
  const [showAddModal, setShowAddModal] = useState(false);
  const [name, setName] = useState("");
  const [priority, setPriority] = useState(1);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!name) return;
    // Generate synthetic masked phone number to ensure zero real PII
    const randomSuffix = Math.floor(1000 + Math.random() * 9000);
    const maskedPhone = `+1 (555) ***-${randomSuffix}`;
    onAddBorrower({ name, phone_number: maskedPhone, priority: Number(priority) });
    setName("");
    setPriority(1);
    setShowAddModal(false);
  };

  const getPriorityBadge = (p) => {
    const colors = {
      1: { bg: "rgba(239, 68, 68, 0.15)", text: "#f87171", label: "P1 Urgent" },
      2: { bg: "rgba(245, 158, 11, 0.15)", text: "#fbbf24", label: "P2 High" },
      3: { bg: "rgba(99, 102, 241, 0.15)", text: "#a5b4fc", label: "P3 Normal" },
      4: { bg: "rgba(100, 116, 139, 0.15)", text: "#94a3b8", label: "P4 Standard" },
      5: { bg: "rgba(100, 116, 139, 0.1)", text: "#64748b", label: "P5 Low" },
    };
    const c = colors[p] || colors[3];
    return (
      <span
        className="badge"
        style={{ backgroundColor: c.bg, color: c.text, border: `1px solid ${c.text}40` }}
      >
        {c.label}
      </span>
    );
  };

  return (
    <div className="panel">
      <div className="panel-header">
        <div className="panel-title">
          <Users size={18} color="var(--accent-purple)" />
          <span>Priority Borrower Queue</span>
          <span className="nav-badge">{borrowers.length} contacts</span>
        </div>

        <button className="btn btn-primary btn-sm" onClick={() => setShowAddModal(true)}>
          <Plus size={14} />
          <span>Add Contact</span>
        </button>
      </div>

      <div className="table-responsive">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Borrower Name</th>
              <th>Masked Telephony Contact</th>
              <th>Queue Priority</th>
              <th>Status</th>
              <th>Attempts</th>
              <th>Last Dialed</th>
            </tr>
          </thead>
          <tbody>
            {borrowers.map((b) => (
              <tr key={b.id}>
                <td style={{ fontFamily: "var(--font-mono)", fontWeight: 600 }}>
                  #{b.id}
                </td>
                <td style={{ fontWeight: 500 }}>{b.name}</td>
                <td>
                  <div style={{ display: "flex", alignItems: "center", gap: "6px", fontFamily: "var(--font-mono)", fontSize: "0.82rem" }}>
                    <ShieldCheck size={14} color="var(--accent-emerald)" title="PII Strictly Masked" />
                    <span>{b.phone_number}</span>
                  </div>
                </td>
                <td>{getPriorityBadge(b.priority)}</td>
                <td>
                  <span
                    className={`badge ${
                      b.call_status === "UNPROCESSED"
                        ? "badge-available"
                        : b.call_status === "CALLING"
                        ? "badge-dialing"
                        : b.call_status === "CONNECTED"
                        ? "badge-connected"
                        : b.call_status === "COMPLETED"
                        ? "badge-completed"
                        : "badge-failed"
                    }`}
                  >
                    {b.call_status}
                  </span>
                </td>
                <td style={{ fontFamily: "var(--font-mono)" }}>{b.attempt_count}</td>
                <td style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}>
                  {b.last_called_at ? new Date(b.last_called_at).toLocaleTimeString() : "Never"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {showAddModal && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h3 style={{ fontSize: "1rem", fontWeight: 600 }}>Add Fictional Borrower</h3>
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => setShowAddModal(false)}
              >
                &times;
              </button>
            </div>
            <form onSubmit={handleSubmit}>
              <div className="modal-body">
                <div className="form-group">
                  <label className="form-label">Full Name</label>
                  <input
                    type="text"
                    className="form-input"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="e.g. Jordan Smith"
                    required
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Queue Priority (1 = Highest)</label>
                  <select
                    className="form-select"
                    value={priority}
                    onChange={(e) => setPriority(e.target.value)}
                  >
                    <option value={1}>Tier 1 - Highest / Urgent</option>
                    <option value={2}>Tier 2 - High</option>
                    <option value={3}>Tier 3 - Normal</option>
                    <option value={4}>Tier 4 - Standard</option>
                    <option value={5}>Tier 5 - Low</option>
                  </select>
                </div>
                <div style={{ fontSize: "0.78rem", color: "var(--accent-cyan)", display: "flex", gap: "6px" }}>
                  <ShieldCheck size={16} />
                  <span>Phone numbers are automatically synthesized and masked with zero real personal data.</span>
                </div>
              </div>
              <div className="modal-footer">
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setShowAddModal(false)}
                >
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  Enqueue Borrower
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
