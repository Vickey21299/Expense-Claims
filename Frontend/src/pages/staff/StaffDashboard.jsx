// StaffDashboard — landing page for staff.
// Shows summary stat cards and a preview of recent claims.

import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Wallet, Clock, CheckCircle, Banknote, PlusCircle, ArrowRight } from "lucide-react";
import StatCard from "../../components/common/StatCard";
import ClaimTable from "../../components/claims/ClaimTable";
import { getMyClaims } from "../../services/api";
import { CURRENT_USER } from "../../data/mockClaims";

function formatAmount(amount, currency = "INR") {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(amount);
}

function getGreeting() {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 18) return "Good afternoon";
  return "Good evening";
}

export default function StaffDashboard() {
  const navigate = useNavigate();
  const [claims, setClaims] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getMyClaims().then((data) => {
      setClaims(data);
      setLoading(false);
    });
  }, []);

  // Compute stats
  const totalSpent = claims
    .filter((c) => ["APPROVED", "READY_FOR_PAYMENT", "PAID"].includes(c.status))
    .reduce((sum, c) => sum + (c.amount || 0), 0);

  const pending = claims.filter((c) =>
    ["SUBMITTED", "UNDER_REVIEW", "FLAGGED", "READY_FOR_PAYMENT"].includes(c.status)
  ).reduce((sum, c) => sum + (c.amount || 0), 0);

  const approved = claims
    .filter((c) => c.status === "APPROVED")
    .reduce((sum, c) => sum + (c.amount || 0), 0);

  const paid = claims
    .filter((c) => c.status === "PAID")
    .reduce((sum, c) => sum + (c.amount || 0), 0);

  const recentClaims = claims
    .filter((c) => c.status !== "DRAFT")
    .slice(0, 5);

  return (
    <div className="page-content">
      {/* Page header */}
      <div className="page-header">
        <div>
          <p className="page-header__greeting">
            {getGreeting()}, {CURRENT_USER.name.split(" ")[0]} 👋
          </p>
          <h1 className="page-header__title">My Expenses</h1>
          <p className="page-header__subtitle">Track and manage your reimbursement claims.</p>
        </div>
        <button
          id="dashboard-add-expense-btn"
          className="btn btn--primary"
          onClick={() => navigate("/add-expense")}
        >
          <PlusCircle size={16} strokeWidth={2} />
          Add Expense
        </button>
      </div>

      {/* Stat cards */}
      {loading ? (
        <div className="stat-grid skeleton-grid">
          {[1, 2, 3, 4].map((n) => (
            <div key={n} className="stat-card skeleton" />
          ))}
        </div>
      ) : (
        <div className="stat-grid">
          <StatCard
            label="Total Approved & Paid"
            value={formatAmount(totalSpent)}
            icon={Wallet}
            colorClass="stat-card--purple"
          />
          <StatCard
            label="Pending Review"
            value={formatAmount(pending)}
            icon={Clock}
            colorClass="stat-card--amber"
          />
          <StatCard
            label="Approved"
            value={formatAmount(approved)}
            icon={CheckCircle}
            colorClass="stat-card--green"
          />
          <StatCard
            label="Paid Out"
            value={formatAmount(paid)}
            icon={Banknote}
            colorClass="stat-card--teal"
          />
        </div>
      )}

      {/* Recent claims */}
      <div className="section">
        <div className="section__header">
          <h2 className="section__title">Recent Claims</h2>
          <button
            id="dashboard-view-all-btn"
            className="btn btn--ghost btn--sm"
            onClick={() => navigate("/claims")}
          >
            View all
            <ArrowRight size={14} strokeWidth={2} />
          </button>
        </div>

        {loading ? (
          <div className="table-skeleton">
            {[1, 2, 3].map((n) => (
              <div key={n} className="table-skeleton__row skeleton" />
            ))}
          </div>
        ) : (
          <ClaimTable claims={recentClaims} showFilterBar={false} />
        )}
      </div>
    </div>
  );
}
