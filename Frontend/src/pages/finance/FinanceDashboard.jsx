// FinanceDashboard.jsx — Primary Finance landing page matching Manager CSS design system.

import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { ShieldCheck, AlertTriangle, CreditCard, IndianRupee, ArrowRight } from "lucide-react";
import StatCard from "../../components/common/StatCard";
import StatusBadge from "../../components/common/StatusBadge";
import { getFinanceDashboard, getFinanceClaims } from "../../services/api";
import { CURRENT_FINANCE } from "../../data/users";

function formatDate(dateStr) {
  if (!dateStr) return "—";
  return new Date(dateStr).toLocaleDateString("en-IN", { day: "2-digit", month: "short" });
}

function formatAmount(amount, currency = "INR") {
  if (!amount && amount !== 0) return "—";
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(amount);
}

export default function FinanceDashboard() {
  const navigate = useNavigate();
  const [metrics, setMetrics] = useState(null);
  const [pendingClaims, setPendingClaims] = useState([]);
  const [flaggedClaims, setFlaggedClaims] = useState([]);
  const [readyClaims, setReadyClaims] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        const [dashMetrics, allFinanceClaims] = await Promise.all([
          getFinanceDashboard(),
          getFinanceClaims(),
        ]);

        setMetrics(dashMetrics);
        setPendingClaims(allFinanceClaims.filter((c) => c.financeStatus === "FINANCE_PENDING").slice(0, 5));
        setFlaggedClaims(allFinanceClaims.filter((c) => c.financeStatus === "FINANCE_EXCEPTION").slice(0, 5));
        setReadyClaims(allFinanceClaims.filter((c) => c.status === "READY_FOR_PAYMENT").slice(0, 5));
      } catch (err) {
        console.error("Failed to load Finance Dashboard data", err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  if (loading) {
    return (
      <div className="page-content">
        <div className="loading-state">
          <div className="spinner" />
          <p>Loading dashboard…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="page-content">
      {/* Header */}
      <div className="page-header">
        <div>
          <p className="page-header__greeting">Welcome back, {CURRENT_FINANCE.name}</p>
          <h1 className="page-header__title">Finance Dashboard</h1>
          <p className="page-header__subtitle">
            Financial verification, anomaly resolution, and reimbursement payment pipeline.
          </p>
        </div>
        <div className="page-header__actions" style={{ display: "flex", gap: "8px" }}>
          <button className="btn btn--primary btn--sm" onClick={() => navigate("/finance/verification")}>
            <ShieldCheck size={14} />
            <span>Verification Queue</span>
          </button>
          <button className="btn btn--ghost btn--sm" onClick={() => navigate("/finance/payments")}>
            <CreditCard size={14} />
            <span>Process Payments</span>
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="stat-grid">
        <StatCard
          label="Pending Verification"
          value={metrics?.pending || 0}
          icon={ShieldCheck}
          colorClass="stat-card--purple"
        />
        <StatCard
          label="Flagged Exceptions"
          value={metrics?.flagged || 0}
          icon={AlertTriangle}
          colorClass="stat-card--amber"
        />
        <StatCard
          label="Ready for Payment"
          value={metrics?.readyForPayment || 0}
          icon={CreditCard}
          colorClass="stat-card--green"
        />
        <StatCard
          label="Monthly Spend"
          value={formatAmount(metrics?.monthlySpend || 0)}
          icon={IndianRupee}
          colorClass="stat-card--teal"
        />
      </div>

      {/* Section 1: Pending Verification */}
      <div className="section">
        <div className="section__header">
          <div>
            <h2 className="section__title">Claims Awaiting Financial Verification</h2>
            <p className="page-header__subtitle" style={{ marginTop: "2px" }}>
              Approved by managers, requiring final finance audit
            </p>
          </div>
          <button
            className="btn btn--ghost btn--sm"
            onClick={() => navigate("/finance/verification?status=FINANCE_PENDING")}
          >
            View all ({metrics?.pending || 0})
          </button>
        </div>

        <div className="claim-table-wrap">
          {pendingClaims.length === 0 ? (
            <div className="empty-state">
              <p className="empty-state__text">No claims currently awaiting verification. 🎉</p>
            </div>
          ) : (
            <div className="table-container">
              <table className="claims-table" aria-label="Claims awaiting verification">
                <thead>
                  <tr>
                    <th>Employee</th>
                    <th>Merchant & Ref</th>
                    <th>Category</th>
                    <th className="text-right">Amount</th>
                    <th>Submitted Date</th>
                    <th>Status</th>
                    <th className="text-right">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {pendingClaims.map((claim) => {
                    const empName = claim.employee?.name || "Employee";
                    const initials = empName.split(" ").map((n) => n[0]).join("").slice(0, 2);

                    return (
                      <tr
                        key={claim.id}
                        className="claims-table__row"
                        onClick={() => navigate(`/finance/claims/${claim.id}`)}
                        role="button"
                        tabIndex={0}
                      >
                        <td>
                          <div className="employee-row">
                            <div className="employee-avatar-sm" aria-hidden="true">
                              {initials}
                            </div>
                            <div className="claims-table__employee">
                              <span className="employee-name">{empName}</span>
                              <span className="claim-id">{claim.employee?.department || "Engineering"}</span>
                            </div>
                          </div>
                        </td>
                        <td className="claims-table__merchant">
                          <span className="merchant-name">{claim.merchant}</span>
                          <span className="claim-id">{claim.claimRef || claim.claim_ref || claim.id}</span>
                        </td>
                        <td className="claims-table__category">{claim.category}</td>
                        <td className="claims-table__amount text-right">
                          {formatAmount(claim.amount, claim.currency)}
                        </td>
                        <td className="claims-table__date">{formatDate(claim.submittedAt || claim.date)}</td>
                        <td className="claims-table__status">
                          <StatusBadge status={claim.financeStatus || claim.status} />
                        </td>
                        <td className="text-right">
                          <button
                            className="btn btn--ghost btn--sm"
                            onClick={(e) => {
                              e.stopPropagation();
                              navigate(`/finance/claims/${claim.id}`);
                            }}
                          >
                            Audit
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* Section 2: Flagged Exceptions */}
      {flaggedClaims.length > 0 && (
        <div className="section" style={{ marginTop: "24px" }}>
          <div className="section__header">
            <div>
              <h2 className="section__title">Flagged / Exception Claims</h2>
              <p className="page-header__subtitle" style={{ marginTop: "2px" }}>
                Requires manual investigation for potential duplicates or policy flags
              </p>
            </div>
            <button
              className="btn btn--ghost btn--sm"
              onClick={() => navigate("/finance/verification?status=FINANCE_EXCEPTION")}
            >
              View all ({metrics?.flagged || 0})
            </button>
          </div>

          <div className="claim-table-wrap">
            <div className="table-container">
              <table className="claims-table" aria-label="Flagged claims">
                <thead>
                  <tr>
                    <th>Employee</th>
                    <th>Merchant & Ref</th>
                    <th>Anomaly Flag Details</th>
                    <th className="text-right">Amount</th>
                    <th>Status</th>
                    <th className="text-right">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {flaggedClaims.map((claim) => {
                    const empName = claim.employee?.name || "Employee";
                    const initials = empName.split(" ").map((n) => n[0]).join("").slice(0, 2);

                    return (
                      <tr
                        key={claim.id}
                        className="claims-table__row"
                        onClick={() => navigate(`/finance/claims/${claim.id}`)}
                        role="button"
                        tabIndex={0}
                      >
                        <td>
                          <div className="employee-row">
                            <div className="employee-avatar-sm" aria-hidden="true">
                              {initials}
                            </div>
                            <div className="claims-table__employee">
                              <span className="employee-name">{empName}</span>
                              <span className="claim-id">{claim.employee?.department || "Engineering"}</span>
                            </div>
                          </div>
                        </td>
                        <td className="claims-table__merchant">
                          <span className="merchant-name">{claim.merchant}</span>
                          <span className="claim-id">{claim.claimRef || claim.claim_ref || claim.id}</span>
                        </td>
                        <td style={{ fontSize: "13px", color: "var(--text)" }}>
                          {claim.duplicate?.assessment || "Potential Duplicate Detected"}
                        </td>
                        <td className="claims-table__amount text-right">
                          {formatAmount(claim.amount, claim.currency)}
                        </td>
                        <td className="claims-table__status">
                          <StatusBadge status="FINANCE_EXCEPTION" />
                        </td>
                        <td className="text-right">
                          <button
                            className="btn btn--danger btn--sm"
                            onClick={(e) => {
                              e.stopPropagation();
                              navigate(`/finance/claims/${claim.id}`);
                            }}
                          >
                            Investigate
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Section 3: Ready for Payment Queue */}
      <div className="section" style={{ marginTop: "24px" }}>
        <div className="section__header">
          <div>
            <h2 className="section__title">Ready for Payment Queue</h2>
            <p className="page-header__subtitle" style={{ marginTop: "2px" }}>
              Cleared claims queued for reimbursement disbursement
            </p>
          </div>
          <button className="btn btn--ghost btn--sm" onClick={() => navigate("/finance/payments")}>
            Process all ({metrics?.readyForPayment || 0})
          </button>
        </div>

        <div className="claim-table-wrap">
          {readyClaims.length === 0 ? (
            <div className="empty-state">
              <p className="empty-state__text">No claims waiting in payment queue.</p>
            </div>
          ) : (
            <div className="table-container">
              <table className="claims-table" aria-label="Ready for payment claims">
                <thead>
                  <tr>
                    <th>Employee</th>
                    <th>Merchant & Ref</th>
                    <th>Category</th>
                    <th className="text-right">Amount</th>
                    <th>Status</th>
                    <th className="text-right">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {readyClaims.map((claim) => {
                    const empName = claim.employee?.name || "Employee";
                    const initials = empName.split(" ").map((n) => n[0]).join("").slice(0, 2);

                    return (
                      <tr
                        key={claim.id}
                        className="claims-table__row"
                        onClick={() => navigate("/finance/payments")}
                        role="button"
                        tabIndex={0}
                      >
                        <td>
                          <div className="employee-row">
                            <div className="employee-avatar-sm" aria-hidden="true">
                              {initials}
                            </div>
                            <div className="claims-table__employee">
                              <span className="employee-name">{empName}</span>
                              <span className="claim-id">{claim.employee?.department || "Engineering"}</span>
                            </div>
                          </div>
                        </td>
                        <td className="claims-table__merchant">
                          <span className="merchant-name">{claim.merchant}</span>
                          <span className="claim-id">{claim.claimRef || claim.claim_ref || claim.id}</span>
                        </td>
                        <td className="claims-table__category">{claim.category}</td>
                        <td className="claims-table__amount text-right">
                          {formatAmount(claim.amount, claim.currency)}
                        </td>
                        <td className="claims-table__status">
                          <StatusBadge status="READY_FOR_PAYMENT" />
                        </td>
                        <td className="text-right">
                          <button
                            className="btn btn--primary btn--sm"
                            onClick={(e) => {
                              e.stopPropagation();
                              navigate("/finance/payments");
                            }}
                          >
                            Pay Now
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
