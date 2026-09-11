// ManagerDashboard — primary manager landing page.
// Shows team stats and claims awaiting review.

import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Clock, CheckCircle2, XCircle, IndianRupee } from "lucide-react";
import StatCard from "../../components/common/StatCard";
import StatusBadge from "../../components/common/StatusBadge";
import { getManagerClaims } from "../../services/api";
import { CURRENT_MANAGER } from "../../data/mockClaims";

function formatDate(dateStr) {
  if (!dateStr) return "—";
  const d = new Date(dateStr);
  const now = new Date();
  const diffMs = now - d;
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays === 0) return "Today";
  if (diffDays === 1) return "Yesterday";
  if (diffDays < 7) return `${diffDays} days ago`;
  return d.toLocaleDateString("en-IN", { day: "2-digit", month: "short" });
}

function formatAmount(amount, currency = "INR") {
  if (!amount && amount !== 0) return "—";
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(amount);
}

const PENDING_STATUSES = ["SUBMITTED", "UNDER_REVIEW", "FLAGGED"];

export default function ManagerDashboard() {
  const navigate = useNavigate();
  const [claims, setClaims] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getManagerClaims().then((data) => {
      setClaims(data);
      setLoading(false);
    });
  }, []);

  const pendingClaims = claims.filter((c) => PENDING_STATUSES.includes(c.status));
  const approvedCount = claims.filter((c) => c.status === "APPROVED").length;
  const rejectedCount = claims.filter((c) => c.status === "REJECTED").length;
  const teamSpend = claims
    .filter((c) => ["APPROVED", "READY_FOR_PAYMENT", "PAID"].includes(c.status))
    .reduce((sum, c) => sum + (c.amount || 0), 0);

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
          <p className="page-header__greeting">Welcome back, {CURRENT_MANAGER.name}</p>
          <h1 className="page-header__title">Manager Dashboard</h1>
          <p className="page-header__subtitle">
            Review and manage reimbursement claims from your team.
          </p>
        </div>
      </div>

      {/* Stats */}
      <div className="stat-grid">
        <StatCard
          label="Pending Review"
          value={pendingClaims.length}
          icon={Clock}
          colorClass="stat-card--amber"
        />
        <StatCard
          label="Approved This Month"
          value={approvedCount}
          icon={CheckCircle2}
          colorClass="stat-card--green"
        />
        <StatCard
          label="Rejected This Month"
          value={rejectedCount}
          icon={XCircle}
          colorClass="stat-card--purple"
        />
        <StatCard
          label="Team Spend"
          value={formatAmount(teamSpend)}
          icon={IndianRupee}
          colorClass="stat-card--teal"
        />
      </div>

      {/* Pending Claims */}
      <div className="section">
        <div className="section__header">
          <h2 className="section__title">Claims Awaiting Your Review</h2>
          {pendingClaims.length > 0 && (
            <button
              className="btn btn--ghost btn--sm"
              onClick={() => navigate("/manager/claims")}
            >
              View all claims
            </button>
          )}
        </div>

        <div className="claim-table-wrap">
          {pendingClaims.length === 0 ? (
            <div className="empty-state">
              <p className="empty-state__text">No claims awaiting review. You're all caught up! 🎉</p>
            </div>
          ) : (
            <div className="table-container">
              <table className="claims-table" aria-label="Claims awaiting review">
                <thead>
                  <tr>
                    <th>Employee</th>
                    <th>Expense</th>
                    <th className="text-right">Amount</th>
                    <th>Submitted</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {pendingClaims.map((claim) => (
                    <tr
                      key={claim.id}
                      className="claims-table__row"
                      onClick={() => navigate(`/manager/claims/${claim.id}`)}
                      role="button"
                      tabIndex={0}
                      aria-label={`Review claim from ${claim.employee?.name}`}
                      onKeyDown={(e) => e.key === "Enter" && navigate(`/manager/claims/${claim.id}`)}
                    >
                      <td>
                        <div className="claims-table__employee">
                          <span className="employee-name">{claim.employee?.name || "—"}</span>
                          <span className="claim-id">{claim.id}</span>
                        </div>
                      </td>
                      <td className="claims-table__merchant">
                        <span className="merchant-name">{claim.merchant}</span>
                        <span className="claim-id">{claim.category}</span>
                      </td>
                      <td className="claims-table__amount text-right">
                        {formatAmount(claim.amount, claim.currency)}
                      </td>
                      <td className="claims-table__date">{formatDate(claim.submittedAt)}</td>
                      <td className="claims-table__status">
                        <StatusBadge status={claim.status} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
