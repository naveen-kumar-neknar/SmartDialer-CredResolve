import React, { useState } from "react";
import { PhoneCall, Shield, LogIn, UserPlus, Lock, Mail, User, CheckCircle2 } from "lucide-react";
import { api } from "../api";

export default function AuthView({ onLoginSuccess }) {
  const [isSignup, setIsSignup] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [role, setRole] = useState("SUPERVISOR");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      if (isSignup) {
        if (!name || !email || !password) {
          throw new Error("Please complete all required fields.");
        }
        const res = await api.signup({ name, email, password, role });
        onLoginSuccess(res.user, res.access_token);
      } else {
        if (!email || !password) {
          throw new Error("Please provide your email and password.");
        }
        const res = await api.login(email, password);
        onLoginSuccess(res.user, res.access_token);
      }
    } catch (err) {
      setError(err.message || "Authentication failed. Please verify your credentials.");
    } finally {
      setLoading(false);
    }
  };

  const fillDemoSupervisor = () => {
    setEmail("supervisor@credresolve.com");
    setPassword("credresolve123");
    setIsSignup(false);
    setError(null);
  };

  const fillDemoAgent = () => {
    setEmail("agent@credresolve.com");
    setPassword("credresolve123");
    setIsSignup(false);
    setError(null);
  };

  return (
    <div style={{
      minHeight: "100vh",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      backgroundColor: "#f8fafc",
      padding: "24px",
      fontFamily: "Inter, -apple-system, BlinkMacSystemFont, sans-serif"
    }}>
      <div style={{
        width: "100%",
        maxWidth: "440px",
        backgroundColor: "#ffffff",
        border: "1px solid #e2e8f0",
        borderRadius: "16px",
        boxShadow: "0 10px 30px rgba(0, 0, 0, 0.04)",
        padding: "40px 36px",
        animation: "fadeIn 0.3s ease-out"
      }}>
        {/* Brand Header */}
        <div style={{ textAlign: "center", marginBottom: "32px" }}>
          <div style={{
            width: "52px",
            height: "52px",
            backgroundColor: "#0f172a",
            color: "#ffffff",
            borderRadius: "12px",
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            marginBottom: "16px"
          }}>
            <PhoneCall size={26} />
          </div>
          <h1 style={{ fontSize: "24px", fontWeight: "700", color: "#0f172a", margin: "0 0 6px 0", letterSpacing: "-0.5px" }}>
            CredResolve SmartDialer
          </h1>
          <p style={{ fontSize: "14px", color: "#64748b", margin: 0 }}>
            Enterprise Telephony Operations & Safety Control
          </p>
        </div>

        {/* Tab Toggle */}
        <div style={{
          display: "flex",
          backgroundColor: "#f1f5f9",
          borderRadius: "8px",
          padding: "4px",
          marginBottom: "24px"
        }}>
          <button
            type="button"
            onClick={() => { setIsSignup(false); setError(null); }}
            style={{
              flex: 1,
              padding: "8px 12px",
              fontSize: "14px",
              fontWeight: "600",
              borderRadius: "6px",
              border: "none",
              cursor: "pointer",
              transition: "all 0.15s ease",
              backgroundColor: !isSignup ? "#ffffff" : "transparent",
              color: !isSignup ? "#0f172a" : "#64748b",
              boxShadow: !isSignup ? "0 1px 3px rgba(0,0,0,0.06)" : "none"
            }}
          >
            Sign In
          </button>
          <button
            type="button"
            onClick={() => { setIsSignup(true); setError(null); }}
            style={{
              flex: 1,
              padding: "8px 12px",
              fontSize: "14px",
              fontWeight: "600",
              borderRadius: "6px",
              border: "none",
              cursor: "pointer",
              transition: "all 0.15s ease",
              backgroundColor: isSignup ? "#ffffff" : "transparent",
              color: isSignup ? "#0f172a" : "#64748b",
              boxShadow: isSignup ? "0 1px 3px rgba(0,0,0,0.06)" : "none"
            }}
          >
            Create Account
          </button>
        </div>

        {error && (
          <div style={{
            backgroundColor: "#fef2f2",
            border: "1px solid #fee2e2",
            color: "#991b1b",
            fontSize: "13px",
            padding: "10px 14px",
            borderRadius: "8px",
            marginBottom: "20px",
            display: "flex",
            alignItems: "center",
            gap: "8px"
          }}>
            <span>{error}</span>
          </div>
        )}

        {/* Auth Form */}
        <form onSubmit={handleSubmit}>
          {isSignup && (
            <div style={{ marginBottom: "16px" }}>
              <label style={{ display: "block", fontSize: "13px", fontWeight: "600", color: "#334155", marginBottom: "6px" }}>
                Full Name
              </label>
              <div style={{ position: "relative" }}>
                <User size={16} style={{ position: "absolute", left: "12px", top: "12px", color: "#94a3b8" }} />
                <input
                  type="text"
                  placeholder="e.g. Priya Sharma"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "10px 12px 10px 36px",
                    border: "1px solid #cbd5e1",
                    borderRadius: "8px",
                    fontSize: "14px",
                    outline: "none",
                    boxSizing: "border-box"
                  }}
                  required={isSignup}
                />
              </div>
            </div>
          )}

          <div style={{ marginBottom: "16px" }}>
            <label style={{ display: "block", fontSize: "13px", fontWeight: "600", color: "#334155", marginBottom: "6px" }}>
              Work Email
            </label>
            <div style={{ position: "relative" }}>
              <Mail size={16} style={{ position: "absolute", left: "12px", top: "12px", color: "#94a3b8" }} />
              <input
                type="email"
                placeholder="name@credresolve.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                style={{
                  width: "100%",
                  padding: "10px 12px 10px 36px",
                  border: "1px solid #cbd5e1",
                  borderRadius: "8px",
                  fontSize: "14px",
                  outline: "none",
                  boxSizing: "border-box"
                }}
                required
              />
            </div>
          </div>

          <div style={{ marginBottom: isSignup ? "16px" : "24px" }}>
            <label style={{ display: "block", fontSize: "13px", fontWeight: "600", color: "#334155", marginBottom: "6px" }}>
              Password
            </label>
            <div style={{ position: "relative" }}>
              <Lock size={16} style={{ position: "absolute", left: "12px", top: "12px", color: "#94a3b8" }} />
              <input
                type="password"
                placeholder="••••••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                style={{
                  width: "100%",
                  padding: "10px 12px 10px 36px",
                  border: "1px solid #cbd5e1",
                  borderRadius: "8px",
                  fontSize: "14px",
                  outline: "none",
                  boxSizing: "border-box"
                }}
                required
              />
            </div>
          </div>

          {isSignup && (
            <div style={{ marginBottom: "24px" }}>
              <label style={{ display: "block", fontSize: "13px", fontWeight: "600", color: "#334155", marginBottom: "6px" }}>
                Role
              </label>
              <select
                value={role}
                onChange={(e) => setRole(e.target.value)}
                style={{
                  width: "100%",
                  padding: "10px 12px",
                  border: "1px solid #cbd5e1",
                  borderRadius: "8px",
                  fontSize: "14px",
                  backgroundColor: "#ffffff",
                  outline: "none",
                  boxSizing: "border-box"
                }}
              >
                <option value="SUPERVISOR">Supervisor / Operations Lead</option>
                <option value="AGENT">Dialer Agent</option>
                <option value="ADMIN">System Administrator</option>
              </select>
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            style={{
              width: "100%",
              padding: "12px",
              backgroundColor: "#0f172a",
              color: "#ffffff",
              border: "none",
              borderRadius: "8px",
              fontSize: "14px",
              fontWeight: "600",
              cursor: loading ? "not-allowed" : "pointer",
              opacity: loading ? 0.7 : 1,
              transition: "background-color 0.15s ease",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: "8px"
            }}
          >
            {isSignup ? <UserPlus size={16} /> : <LogIn size={16} />}
            <span>{loading ? "Authenticating..." : isSignup ? "Create Account" : "Sign In to Operations"}</span>
          </button>
        </form>

        {/* Demo Fast-Login Assist for Reviewers */}
        <div style={{
          marginTop: "28px",
          paddingTop: "20px",
          borderTop: "1px solid #f1f5f9",
          textAlign: "center"
        }}>
          <p style={{ fontSize: "12px", color: "#64748b", margin: "0 0 10px 0", fontWeight: "500" }}>
            Quick Reviewer Login:
          </p>
          <div style={{ display: "flex", gap: "8px", justifyContent: "center" }}>
            <button
              type="button"
              onClick={fillDemoSupervisor}
              style={{
                fontSize: "12px",
                padding: "6px 12px",
                border: "1px solid #e2e8f0",
                borderRadius: "6px",
                backgroundColor: "#f8fafc",
                color: "#0f172a",
                cursor: "pointer",
                fontWeight: "500"
              }}
            >
              Supervisor Demo
            </button>
            <button
              type="button"
              onClick={fillDemoAgent}
              style={{
                fontSize: "12px",
                padding: "6px 12px",
                border: "1px solid #e2e8f0",
                borderRadius: "6px",
                backgroundColor: "#f8fafc",
                color: "#0f172a",
                cursor: "pointer",
                fontWeight: "500"
              }}
            >
              Agent Demo
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
