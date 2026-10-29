import React, { useState, useEffect, useCallback } from "react";
import Sidebar from "./components/Sidebar";
import Header from "./components/Header";
import MetricCards from "./components/MetricCards";
import CallsTable from "./components/CallsTable";
import AgentsTable from "./components/AgentsTable";
import BorrowersTable from "./components/BorrowersTable";
import PacingSimulationWidget from "./components/PacingSimulationWidget";
import SafetyDecisionsTable from "./components/SafetyDecisionsTable";
import TelecomProviderPanel from "./components/TelecomProviderPanel";
import CallDetailModal from "./components/CallDetailModal";
import AuthView from "./components/AuthView";
import { api } from "./api";
import { Play, Calculator, AlertCircle, CheckCircle2, RotateCcw } from "lucide-react";

export default function App() {
  const [currentUser, setCurrentUser] = useState(() => {
    try {
      const saved = localStorage.getItem("smartdialer_user");
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });

  const [activeTab, setActiveTab] = useState("overview");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState(null);

  // Core Data
  const [stats, setStats] = useState(null);
  const [calls, setCalls] = useState([]);
  const [agents, setAgents] = useState([]);
  const [borrowers, setBorrowers] = useState([]);
  const [decisions, setDecisions] = useState([]);
  const [providerHealth, setProviderHealth] = useState(null);

  // Interactive state
  const [pacingSimResult, setPacingSimResult] = useState(null);
  const [selectedCallDetail, setSelectedCallDetail] = useState(null);

  // Fetch all system data
  const loadData = useCallback(async (showSpinner = false) => {
    if (showSpinner) setLoading(true);
    try {
      const [statsData, callsData, agentsData, borrowersData, decisionsData, providerData] =
        await Promise.all([
          api.getDashboardStats().catch(() => null),
          api.getCalls("", 50).catch(() => []),
          api.getAgents().catch(() => []),
          api.getBorrowers().catch(() => []),
          api.getSafetyDecisions(50).catch(() => []),
          api.getProviderHealth().catch(() => null),
        ]);

      if (statsData) setStats(statsData);
      setCalls(callsData || []);
      setAgents(agentsData || []);
      setBorrowers(borrowersData || []);
      setDecisions(decisionsData || []);
      if (providerData) setProviderHealth(providerData);
      setError(null);
    } catch (err) {
      console.error("Failed to load dashboard data:", err);
      setError("Unable to connect to SmartDialer API gateway. Ensure backend is running.");
    } finally {
      if (showSpinner) setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData(true);
    const interval = setInterval(() => loadData(false), 8000);
    return () => clearInterval(interval);
  }, [loadData]);

  // Handler: Seed Demo Data
  const handleSeedDemo = async () => {
    setLoading(true);
    try {
      const res = await api.seedDemoData();
      setNotice(res.message);
      await loadData(false);
    } catch (err) {
      setError(err.message || "Failed to seed demo data");
    } finally {
      setLoading(false);
    }
  };

  // Handler: Recover Stale Reservations
  const handleRunRecovery = async () => {
    setLoading(true);
    try {
      const res = await api.runRecovery();
      const { recovered_agents, recovered_borrowers } = res.result;
      setNotice(
        `Reservation Recovery completed: ${recovered_agents} stale agents freed, ${recovered_borrowers} borrowers re-enqueued.`
      );
      await loadData(false);
    } catch (err) {
      setError(err.message || "Failed to run recovery");
    } finally {
      setLoading(false);
    }
  };

  // Handler: Progressive Dialing
  const handleStartProgressive = async (batchSize = 1) => {
    setLoading(true);
    try {
      const res = await api.startProgressiveDialing(batchSize);
      if (res.status === "SUCCESS") {
        setNotice(`Progressive dialer dispatched ${res.calls_initiated} call session(s).`);
      } else {
        setNotice(`Dialer: ${res.message} [Decision: ${res.safety_decision || "HALTED"}]`);
      }
      await loadData(false);
    } catch (err) {
      setError(err.message || "Progressive dialing allocation failed");
    } finally {
      setLoading(false);
    }
  };

  // Handler: Predictive Pacing Simulation
  const handleSimulatePredictive = async (answerRate, duration) => {
    setLoading(true);
    try {
      const res = await api.simulatePredictivePacing(answerRate, duration);
      setPacingSimResult(res);
      await loadData(false);
    } catch (err) {
      setError(err.message || "Predictive simulation failed");
    } finally {
      setLoading(false);
    }
  };

  // Handler: Agent Status Change
  const handleAgentStatusChange = async (agentId, newStatus) => {
    try {
      await api.updateAgentStatus(agentId, newStatus);
      setNotice(`Agent #${agentId} status updated to ${newStatus}.`);
      await loadData(false);
    } catch (err) {
      setError(err.message || "Invalid agent status transition");
    }
  };

  // Handler: Simulate Call State Transition
  const handleSimulateCall = async (callId, targetStatus, reason = null) => {
    try {
      await api.simulateCall(callId, targetStatus, reason);
      setNotice(`Call #${callId} moved to ${targetStatus}.`);
      await loadData(false);
    } catch (err) {
      setError(err.message || `Failed to transition call to ${targetStatus}`);
    }
  };

  // Handler: View Call Detail
  const handleViewCallDetail = async (callId) => {
    try {
      const detail = await api.getCallDetail(callId);
      setSelectedCallDetail(detail);
    } catch (err) {
      setError("Failed to fetch call details");
    }
  };

  // Handler: Add Borrower
  const handleAddBorrower = async (borrowerData) => {
    try {
      await api.createBorrower(borrowerData);
      setNotice(`Borrower "${borrowerData.name}" added to priority queue.`);
      await loadData(false);
    } catch (err) {
      setError(err.message || "Failed to create borrower");
    }
  };

  // Handler: Provider Configuration
  const handleUpdateProviderConfig = async (config) => {
    setLoading(true);
    try {
      const res = await api.updateProviderConfig(config);
      setNotice(res.message);
      await loadData(false);
    } catch (err) {
      setError(err.message || "Failed to update provider configuration");
    } finally {
      setLoading(false);
    }
  };

  // Handler: Provider Outage Toggle
  const handleToggleOutage = async (providerName, enableOutage) => {
    setLoading(true);
    try {
      await api.toggleProviderOutage(providerName, enableOutage);
      setNotice(
        enableOutage
          ? `Simulated total OUTAGE triggered for ${providerName}. Safety Controller will halt all calls.`
          : `Outage restored for ${providerName}. Normal routing resumed.`
      );
      await loadData(false);
    } catch (err) {
      setError(err.message || "Failed to toggle provider outage");
    } finally {
      setLoading(false);
    }
  };

  // Handler: Send Webhook Event
  const handleSendWebhookEvent = async (eventData) => {
    try {
      const res = await api.sendProviderWebhookEvent(eventData);
      await loadData(false);
      return res;
    } catch (err) {
      setError(err.message || "Webhook event delivery failed");
      throw err;
    }
  };

  // Session Handlers
  const handleLoginSuccess = (user, token) => {
    setCurrentUser(user);
    try {
      localStorage.setItem("smartdialer_user", JSON.stringify(user));
      localStorage.setItem("smartdialer_token", token);
    } catch (e) {}
    loadData(true);
  };

  const handleLogout = async () => {
    try {
      await api.logout();
    } catch (e) {}
    setCurrentUser(null);
    try {
      localStorage.removeItem("smartdialer_user");
      localStorage.removeItem("smartdialer_token");
    } catch (e) {}
  };

  if (!currentUser) {
    return <AuthView onLoginSuccess={handleLoginSuccess} />;
  }

  return (
    <div className="app-container">
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        stats={stats}
        currentUser={currentUser}
        onLogout={handleLogout}
      />

      <div className="main-wrapper">
        <Header
          activeTab={activeTab}
          stats={stats}
          loading={loading}
          onRefresh={() => loadData(true)}
          onSeedDemo={handleSeedDemo}
          onRunRecovery={handleRunRecovery}
          currentUser={currentUser}
          onLogout={handleLogout}
        />

        <main className="content-body">
          {/* Error Banner */}
          {error && (
            <div className="alert-banner alert-error">
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <AlertCircle size={18} />
                <span>{error}</span>
              </div>
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => setError(null)}
                style={{ padding: "2px 8px" }}
              >
                &times;
              </button>
            </div>
          )}

          {/* Notice Banner */}
          {notice && (
            <div className="alert-banner alert-success">
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <CheckCircle2 size={18} />
                <span>{notice}</span>
              </div>
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => setNotice(null)}
                style={{ padding: "2px 8px" }}
              >
                &times;
              </button>
            </div>
          )}

          {/* High-Level Operational Metrics */}
          <MetricCards stats={stats} />

          {/* Tab Views */}
          {activeTab === "overview" && (
            <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
              {/* Quick Actions Panel */}
              <div className="panel">
                <div className="panel-header">
                  <div className="panel-title">
                    <span>Campaign Quick Actions</span>
                  </div>
                </div>
                <div className="panel-body" style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
                  <button
                    className="btn btn-primary"
                    onClick={() => handleStartProgressive(1)}
                    disabled={loading || (stats?.available_agents === 0)}
                  >
                    <Play size={16} />
                    <span>Dial 1 Progressive Call</span>
                  </button>

                  <button
                    className="btn btn-secondary"
                    onClick={() => {
                      setActiveTab("dialer");
                      handleSimulatePredictive(0.35, 120);
                    }}
                  >
                    <Calculator size={16} />
                    <span>Open Predictive Pacing Calculator</span>
                  </button>

                  {agents.length === 0 && (
                    <button className="btn btn-secondary" onClick={handleSeedDemo}>
                      <span>Seed Initial 25 Borrowers & Agents</span>
                    </button>
                  )}
                </div>
              </div>

              {/* Call Sessions Preview */}
              <CallsTable
                calls={calls.slice(0, 10)}
                onSimulateCall={handleSimulateCall}
                onViewDetails={handleViewCallDetail}
              />

              {/* Agent Fleet Preview */}
              <AgentsTable
                agents={agents}
                onStatusChange={handleAgentStatusChange}
              />
            </div>
          )}

          {activeTab === "dialer" && (
            <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
              <PacingSimulationWidget
                onRunPredictiveSimulation={handleSimulatePredictive}
                onStartProgressiveDialing={handleStartProgressive}
                simulationResult={pacingSimResult}
                loading={loading}
              />
              <SafetyDecisionsTable decisions={decisions.slice(0, 15)} />
            </div>
          )}

          {activeTab === "calls" && (
            <CallsTable
              calls={calls}
              onSimulateCall={handleSimulateCall}
              onViewDetails={handleViewCallDetail}
            />
          )}

          {activeTab === "agents" && (
            <AgentsTable
              agents={agents}
              onStatusChange={handleAgentStatusChange}
            />
          )}

          {activeTab === "borrowers" && (
            <BorrowersTable
              borrowers={borrowers}
              onAddBorrower={handleAddBorrower}
            />
          )}

          {activeTab === "safety" && (
            <SafetyDecisionsTable decisions={decisions} />
          )}

          {activeTab === "telecom" && (
            <TelecomProviderPanel
              providerHealth={providerHealth}
              onUpdateConfig={handleUpdateProviderConfig}
              onToggleOutage={handleToggleOutage}
              onSendWebhookEvent={handleSendWebhookEvent}
              loading={loading}
            />
          )}
        </main>
      </div>

      {/* Call Detail Inspection Modal */}
      {selectedCallDetail && (
        <CallDetailModal
          call={selectedCallDetail}
          onClose={() => setSelectedCallDetail(null)}
        />
      )}
    </div>
  );
}
