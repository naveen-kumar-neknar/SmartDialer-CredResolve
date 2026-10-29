import React, { useState } from "react";
import { Sliders, ShieldCheck, Play, Calculator, AlertTriangle, ShieldAlert } from "lucide-react";

export default function PacingSimulationWidget({
  onRunPredictiveSimulation,
  onStartProgressiveDialing,
  simulationResult,
  loading,
}) {
  const [answerRate, setAnswerRate] = useState(0.35);
  const [duration, setDuration] = useState(120);
  const [progressiveBatchSize, setProgressiveBatchSize] = useState(1);

  const handlePredictiveSimulate = () => {
    onRunPredictiveSimulation(Number(answerRate), Number(duration));
  };

  const handleStartProgressive = () => {
    onStartProgressiveDialing(Number(progressiveBatchSize));
  };

  const getDecisionBadge = (decision) => {
    switch (decision) {
      case "APPROVED":
        return <span className="badge badge-completed">SAFETY APPROVED</span>;
      case "REDUCED":
        return <span className="badge badge-paused">THROTTLED / REDUCED</span>;
      case "FALLBACK_PROGRESSIVE":
        return <span className="badge badge-dialing">FALLBACK TO PROGRESSIVE</span>;
      case "REJECTED":
        return <span className="badge badge-failed">SAFETY HALTED / REJECTED</span>;
      default:
        return <span className="badge badge-offline">{decision || "PENDING"}</span>;
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      <div className="controls-grid">
        {/* Progressive Dialer Execution Card */}
        <div className="control-card" style={{ borderColor: "rgba(99, 102, 241, 0.4)" }}>
          <div className="control-title" style={{ color: "var(--accent-primary)" }}>
            <Play size={18} />
            <span>Progressive Call Allocator (Live)</span>
          </div>
          <p className="control-desc">
            Executes a real progressive batch. Atomically locks and reserves 1 available agent
            per borrower before initiating call dispatch via telephony gateway.
          </p>

          <div className="form-group" style={{ marginTop: "8px" }}>
            <label className="form-label">Batch Size (Max Calls)</label>
            <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
              <select
                className="form-select"
                value={progressiveBatchSize}
                onChange={(e) => setProgressiveBatchSize(e.target.value)}
                style={{ flex: 1 }}
              >
                <option value={1}>1 Call (Strict 1:1)</option>
                <option value={2}>2 Calls</option>
                <option value={3}>3 Calls</option>
                <option value={5}>5 Calls</option>
              </select>
              <button
                className="btn btn-primary"
                onClick={handleStartProgressive}
                disabled={loading}
              >
                <Play size={15} />
                <span>Dial Batch</span>
              </button>
            </div>
          </div>

          <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", display: "flex", gap: "6px" }}>
            <ShieldCheck size={14} color="var(--accent-emerald)" />
            <span>Guarantees zero call drops by reserving agent capacity prior to dial.</span>
          </div>
        </div>

        {/* Predictive Pacing Simulator Card */}
        <div className="control-card">
          <div className="control-title" style={{ color: "var(--accent-cyan)" }}>
            <Calculator size={18} />
            <span>Predictive Pacing Engine (Simulation)</span>
          </div>
          <p className="control-desc">
            Rule-based statistical engine calculating expected connections based on answer rates
            and turnover times. <strong>Never creates calls directly.</strong>
          </p>

          <div className="slider-container">
            <div className="slider-label">
              <span className="form-label">Historical Answer Rate</span>
              <span style={{ fontFamily: "var(--font-mono)", fontWeight: 600, color: "var(--accent-cyan)" }}>
                {(answerRate * 100).toFixed(0)}%
              </span>
            </div>
            <input
              type="range"
              min="0.05"
              max="0.95"
              step="0.05"
              value={answerRate}
              onChange={(e) => setAnswerRate(e.target.value)}
            />
          </div>

          <div className="slider-container">
            <div className="slider-label">
              <span className="form-label">Average Call Duration</span>
              <span style={{ fontFamily: "var(--font-mono)", fontWeight: 600, color: "var(--accent-cyan)" }}>
                {duration} seconds
              </span>
            </div>
            <input
              type="range"
              min="30"
              max="300"
              step="15"
              value={duration}
              onChange={(e) => setDuration(e.target.value)}
            />
          </div>

          <button
            className="btn btn-secondary"
            onClick={handlePredictiveSimulate}
            disabled={loading}
            style={{ marginTop: "4px" }}
          >
            <Sliders size={15} />
            <span>Simulate Pacing Proposal</span>
          </button>
        </div>
      </div>

      {/* Safety Controller Decision Panel */}
      {simulationResult && (
        <div className="panel" style={{ borderLeft: "4px solid var(--accent-primary)" }}>
          <div className="panel-header">
            <div className="panel-title">
              <ShieldAlert size={18} color="var(--accent-primary)" />
              <span>Safety Controller Evaluation Result</span>
              {getDecisionBadge(simulationResult.decision)}
            </div>
          </div>
          <div className="panel-body" style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "16px" }}>
              <div style={{ background: "#f8fafc", padding: "14px", borderRadius: "8px", border: "1px solid var(--border-color)" }}>
                <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Engine Proposed Calls</div>
                <div style={{ fontSize: "1.6rem", fontWeight: 700, color: "var(--text-primary)" }}>
                  {simulationResult.engine_proposed_calls}
                </div>
              </div>
              <div style={{ background: "#f8fafc", padding: "14px", borderRadius: "8px", border: "1px solid var(--border-color)" }}>
                <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Safety Approved Calls</div>
                <div style={{ fontSize: "1.6rem", fontWeight: 700, color: "var(--accent-emerald)" }}>
                  {simulationResult.approved_calls}
                </div>
              </div>
              <div style={{ background: "#f8fafc", padding: "14px", borderRadius: "8px", border: "1px solid var(--border-color)" }}>
                <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Rule Triggered</div>
                <div style={{ fontSize: "0.95rem", fontWeight: 600, color: "var(--text-primary)", marginTop: "4px" }}>
                  {simulationResult.rule_triggered}
                </div>
              </div>
            </div>

            <div>
              <div style={{ fontSize: "0.8rem", fontWeight: 600, color: "var(--text-secondary)", marginBottom: "4px" }}>
                Safety Officer Verdict & Justification:
              </div>
              <div style={{ background: "#f8fafc", padding: "12px 16px", borderRadius: "8px", border: "1px solid var(--border-color)", fontSize: "0.88rem", color: "var(--text-primary)" }}>
                {simulationResult.reason}
              </div>
            </div>

            <div>
              <div style={{ fontSize: "0.8rem", fontWeight: 600, color: "var(--text-secondary)", marginBottom: "4px" }}>
                Mathematical Calculation Breakdown:
              </div>
              <div className="code-block">
                {simulationResult.formula_explanation}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
