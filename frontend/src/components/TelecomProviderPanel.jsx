import React, { useState } from "react";
import { Radio, AlertOctagon, Zap, ShieldAlert, Copy, RefreshCw, Send } from "lucide-react";

export default function TelecomProviderPanel({
  providerHealth,
  onUpdateConfig,
  onToggleOutage,
  onSendWebhookEvent,
  loading,
}) {
  const [selectedProvider, setSelectedProvider] = useState(providerHealth?.active_provider || "ProviderA");
  const [simulateFailure, setSimulateFailure] = useState(
    providerHealth?.stats?.provider_b?.settings?.simulate_failure || false
  );
  const [simulateTimeout, setSimulateTimeout] = useState(
    providerHealth?.stats?.provider_b?.settings?.simulate_timeout || false
  );
  const [simulateDuplicate, setSimulateDuplicate] = useState(
    providerHealth?.stats?.provider_b?.settings?.simulate_duplicate || false
  );
  const [simulateOutOfOrder, setSimulateOutOfOrder] = useState(
    providerHealth?.stats?.provider_b?.settings?.simulate_out_of_order || false
  );

  const [testEventCallId, setTestEventCallId] = useState(1);
  const [testEventType, setTestEventType] = useState("RINGING");
  const [testEventResult, setTestEventResult] = useState(null);

  const handleApplyConfig = () => {
    onUpdateConfig({
      active_provider: selectedProvider,
      simulate_failure: simulateFailure,
      simulate_timeout: simulateTimeout,
      simulate_duplicate: simulateDuplicate,
      simulate_out_of_order: simulateOutOfOrder,
    });
  };

  const handleTestDuplicateWebhook = async () => {
    const fixedEventId = `test-dup-${Date.now()}`;
    // 1st dispatch
    const res1 = await onSendWebhookEvent({
      event_id: fixedEventId,
      call_id: Number(testEventCallId),
      provider: selectedProvider,
      event_type: testEventType,
      sequence_number: 2,
    });
    // 2nd dispatch with exact same event_id to prove idempotency
    const res2 = await onSendWebhookEvent({
      event_id: fixedEventId,
      call_id: Number(testEventCallId),
      provider: selectedProvider,
      event_type: testEventType,
      sequence_number: 2,
    });

    setTestEventResult({
      first_dispatch: res1,
      second_dispatch_idempotent: res2,
      tested_event_id: fixedEventId,
    });
  };

  const provAStats = providerHealth?.stats?.provider_a || {};
  const provBStats = providerHealth?.stats?.provider_b || {};

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      <div className="controls-grid">
        {/* Provider A Card */}
        <div
          className="control-card"
          style={{
            borderColor: selectedProvider === "ProviderA" ? "var(--accent-primary)" : "var(--border-color)",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div className="control-title" style={{ color: "var(--text-primary)" }}>
              <Zap size={18} color="var(--accent-emerald)" />
              <span>Provider A (Tier 1 Gateway)</span>
            </div>
            <span
              className={`badge ${
                providerHealth?.provider_a_health === "HEALTHY" ? "badge-available" : "badge-failed"
              }`}
            >
              {providerHealth?.provider_a_health || "HEALTHY"}
            </span>
          </div>

          <p className="control-desc">
            Production-grade telecom carrier. Low latency (10-40ms), strict FIFO sequence delivery,
            and &gt;98% connection reliability.
          </p>

          <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", display: "flex", flexDirection: "column", gap: "4px" }}>
            <div>Requests Routed: <strong>{provAStats.requests || 0}</strong></div>
            <div>Carrier Failures: <strong>{provAStats.failures || 0}</strong></div>
          </div>

          <div style={{ display: "flex", gap: "8px", marginTop: "auto" }}>
            <button
              className={`btn btn-sm ${selectedProvider === "ProviderA" ? "btn-primary" : "btn-secondary"}`}
              onClick={() => {
                setSelectedProvider("ProviderA");
                onUpdateConfig({ active_provider: "ProviderA" });
              }}
              disabled={loading}
              style={{ flex: 1 }}
            >
              {selectedProvider === "ProviderA" ? "Active Gateway" : "Switch to Provider A"}
            </button>
            <button
              className="btn btn-danger btn-sm"
              onClick={() => onToggleOutage("ProviderA", !provAStats.force_outage)}
              disabled={loading}
            >
              {provAStats.force_outage ? "Restore A" : "Simulate Outage"}
            </button>
          </div>
        </div>

        {/* Provider B Card */}
        <div
          className="control-card"
          style={{
            borderColor: selectedProvider === "ProviderB" ? "var(--accent-primary)" : "var(--border-color)",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div className="control-title" style={{ color: "var(--text-primary)" }}>
              <AlertOctagon size={18} color="var(--accent-amber)" />
              <span>Provider B (Chaos & Latency)</span>
            </div>
            <span
              className={`badge ${
                providerHealth?.provider_b_health === "HEALTHY"
                  ? "badge-available"
                  : providerHealth?.provider_b_health === "DEGRADED"
                  ? "badge-paused"
                  : "badge-failed"
              }`}
            >
              {providerHealth?.provider_b_health || "HEALTHY"}
            </span>
          </div>

          <p className="control-desc">
            Simulated volatile telecom trunk. Generates latency spikes (100-250ms), timeouts,
            duplicate webhook webhooks, and out-of-order events.
          </p>

          <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", display: "flex", flexDirection: "column", gap: "4px" }}>
            <div>Requests Routed: <strong>{provBStats.requests || 0}</strong></div>
            <div>Timeouts / Failures: <strong>{provBStats.timeouts || 0} / {provBStats.failures || 0}</strong></div>
          </div>

          <div style={{ display: "flex", gap: "8px", marginTop: "auto" }}>
            <button
              className={`btn btn-sm ${selectedProvider === "ProviderB" ? "btn-primary" : "btn-secondary"}`}
              onClick={() => {
                setSelectedProvider("ProviderB");
                onUpdateConfig({ active_provider: "ProviderB" });
              }}
              disabled={loading}
              style={{ flex: 1 }}
            >
              {selectedProvider === "ProviderB" ? "Active Gateway" : "Switch to Provider B"}
            </button>
            <button
              className="btn btn-danger btn-sm"
              onClick={() => onToggleOutage("ProviderB", !provBStats.force_outage)}
              disabled={loading}
            >
              {provBStats.force_outage ? "Restore B" : "Simulate Outage"}
            </button>
          </div>
        </div>
      </div>

      {/* Provider B Chaos Injection Controls */}
      <div className="panel">
        <div className="panel-header">
          <div className="panel-title">
            <Radio size={18} color="var(--accent-amber)" />
            <span>Provider B Chaos Injection Parameters</span>
          </div>
          <button className="btn btn-primary btn-sm" onClick={handleApplyConfig} disabled={loading}>
            <RefreshCw size={14} />
            <span>Apply Parameters</span>
          </button>
        </div>
        <div className="panel-body">
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "16px" }}>
            <label style={{ display: "flex", alignItems: "center", gap: "10px", cursor: "pointer", fontSize: "0.88rem" }}>
              <input
                type="checkbox"
                checked={simulateFailure}
                onChange={(e) => setSimulateFailure(e.target.checked)}
              />
              <span>Simulate Carrier Circuit Failure (503)</span>
            </label>

            <label style={{ display: "flex", alignItems: "center", gap: "10px", cursor: "pointer", fontSize: "0.88rem" }}>
              <input
                type="checkbox"
                checked={simulateTimeout}
                onChange={(e) => setSimulateTimeout(e.target.checked)}
              />
              <span>Simulate Gateway Timeout (504)</span>
            </label>

            <label style={{ display: "flex", alignItems: "center", gap: "10px", cursor: "pointer", fontSize: "0.88rem" }}>
              <input
                type="checkbox"
                checked={simulateDuplicate}
                onChange={(e) => setSimulateDuplicate(e.target.checked)}
              />
              <span>Simulate Duplicate Webhook Delivery</span>
            </label>

            <label style={{ display: "flex", alignItems: "center", gap: "10px", cursor: "pointer", fontSize: "0.88rem" }}>
              <input
                type="checkbox"
                checked={simulateOutOfOrder}
                onChange={(e) => setSimulateOutOfOrder(e.target.checked)}
              />
              <span>Simulate Out-Of-Order Event Arrival</span>
            </label>
          </div>
        </div>
      </div>

      {/* Webhook Idempotency & Out-of-Order Interactive Tester */}
      <div className="panel">
        <div className="panel-header">
          <div className="panel-title">
            <Copy size={18} color="var(--accent-cyan)" />
            <span>Interactive Webhook Idempotency & Sequence Tester</span>
          </div>
        </div>
        <div className="panel-body" style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}>
            Sends duplicate identical webhook events to test that the Event Processor detects the duplicate,
            acknowledges the provider with 200 OK, and enforces strict idempotency without producing multiple state transitions.
          </p>

          <div style={{ display: "flex", gap: "12px", alignItems: "center", flexWrap: "wrap" }}>
            <div className="form-group" style={{ width: "140px" }}>
              <label className="form-label">Target Call ID</label>
              <input
                type="number"
                className="form-input"
                value={testEventCallId}
                onChange={(e) => setTestEventCallId(e.target.value)}
                min="1"
              />
            </div>

            <div className="form-group" style={{ width: "160px" }}>
              <label className="form-label">Event Type</label>
              <select
                className="form-select"
                value={testEventType}
                onChange={(e) => setTestEventType(e.target.value)}
              >
                <option value="RINGING">RINGING</option>
                <option value="CONNECTED">CONNECTED</option>
                <option value="COMPLETED">COMPLETED</option>
                <option value="FAILED">FAILED</option>
              </select>
            </div>

            <button
              className="btn btn-secondary"
              onClick={handleTestDuplicateWebhook}
              disabled={loading}
              style={{ marginTop: "18px" }}
            >
              <Send size={14} />
              <span>Fire Duplicate Webhook Test</span>
            </button>
          </div>

          {testEventResult && (
            <div style={{ marginTop: "12px" }}>
              <div style={{ fontSize: "0.8rem", fontWeight: 600, color: "var(--text-secondary)", marginBottom: "4px" }}>
                Idempotency Verification Log (Event ID: {testEventResult.tested_event_id}):
              </div>
              <div className="code-block">
                {JSON.stringify(testEventResult, null, 2)}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
