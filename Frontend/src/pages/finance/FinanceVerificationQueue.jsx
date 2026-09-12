// FinanceVerificationQueue.jsx — Filterable verification queue matching Manager CSS design.

import { useState, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Search } from "lucide-react";
import { getFinanceClaims } from "../../services/api";
import StatusBadge from "../../components/common/StatusBadge";

const STATUS_TABS = [
  { key: "ALL", label: "All Claims" },
  { key: "FINANCE_PENDING", label: "Pending Verification" },
  { key: "FINANCE_EXCEPTION", label: "Flagged / Exceptions" },
  { key: "FINANCE_CLEARED", label: "Cleared" },
  { key: "FINANCE_REJECTED", label: "Rejected" },
  { key: "PAID", label: "Paid" },
];

function formatDate(dateStr) {
  if (!dateStr) return "—";
  return new Date(dateStr).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
}

function formatAmount(amount, currency = "INR") {
  if (!amount && amount !== 0) return "—";
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(amount);
}

export default function FinanceVerificationQueue() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const initialStatus = searchParams.get("status") || "ALL";

  const [activeTab, setActiveTab] = useState(initialStatus);
  const [searchQuery, setSearchQuery] = useState("");
  const [claims, setClaims] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadClaims();
  }, [activeTab]);

  async function loadClaims() {
    try {
      setLoading(true);
      const data = await getFinanceClaims({
        financeStatus: activeTab,
      });
      setClaims(data);
    } catch (err) {
      console.error("Error loading verification queue", err);
    } finally {
      setLoading(false);
    }
  }

  const handleTabChange = (key) => {
    setActiveTab(key);
    setSearchParams({ status: key });
  };

  // Filter search locally
  let filtered = claims;
  if (searchQuery.trim()) {
    const q = searchQuery.toLowerCase();
    filtered = filtered.filter(
      (c) =>
        (c.employee?.name || "").toLowerCase().includes(q) ||
        (c.merchant || "").toLowerCase().includes(q) ||
        (c.id || "").toLowerCase().includes(q)
    );
  }

  if (loading) {
    return (
      <div className="page-content">
        <div className="loading-state">
          <div className="spinner" />
          <p>Loading verification queue…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="page-content">
      {/* Header */}
      <div className="page-header">
        <div>
          <h1 className="page-header__title">Verification Queue</h1>
          <p className="page-header__subtitle">
            Inspect manager-approved claims, verify policy compliance, and resolve flagged exceptions.
          </p>
        </div>
      </div>

      {/* Search Bar */}
      <div className="search-bar">
        <Search size={16} strokeWidth={2} className="search-bar__icon" />
        <input
          id="fin-search-input"
          type="text"
          className="search-bar__input"
          placeholder="Search employee, merchant, or claim ID…"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
      </div>

      {/* Filter Tabs & Table */}
      <div className="claim-table-wrap">
        <div className="filter-bar" role="tablist" aria-label="Filter claims by status">
          {STATUS_TABS.map((tab) => (
            <button
              key={tab.key}
              role="tab"
              aria-selected={activeTab === tab.key}
              className={`filter-tab ${activeTab === tab.key ? "filter-tab--active" : ""}`}
              onClick={() => handleTabChange(tab.key)}
              id={`fin-tab-${tab.key.toLowerCase()}`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {filtered.length === 0 ? (
          <div className="empty-state">
            <p className="empty-state__text">No claims match the selected criteria.</p>
          </div>
        ) : (
          <div className="table-container">
            <table className="claims-table" aria-label="Finance verification queue">
              <thead>
                <tr>
                  <th>Employee</th>
                  <th>Timeline</th>
                  <th>Merchant & Ref</th>
                  <th>Category</th>
                  <th className="text-right">Amount</th>
                  <th>Verification Status</th>
                  <th>Audit Decision</th>
                  <th className="text-right">Action</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((claim) => {
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
                      <td className="claims-table__initiated">
                        <div className="initiated-cell">
                          <span className="initiated-date">{formatDate(claim.submittedAt || claim.createdAt || claim.date)}</span>
                          <span className="initiated-time">Exp: {formatDate(claim.date)}</span>
                        </div>
                      </td>
                      <td className="claims-table__merchant">
                        <span className="merchant-name">{claim.merchant}</span>
                        <span className="claim-id">{claim.claimRef || claim.claim_ref || claim.id}</span>
                      </td>
                      <td className="claims-table__category">{claim.category || "—"}</td>
                      <td className="claims-table__amount text-right">
                        {formatAmount(claim.amount, claim.currency)}
                      </td>
                      <td className="claims-table__status">
                        <div style={{ display: "flex", flexDirection: "column", gap: "3px", alignItems: "flex-start" }}>
                          <StatusBadge status={claim.status} />
                          {claim.duplicate_risk_percentage != null && claim.duplicate_risk_percentage > 30 && (
                            <span
                              className={`claim-risk-pill ${
                                claim.duplicate_risk_percentage >= 70
                                  ? "claim-risk-pill--high"
                                  : "claim-risk-pill--medium"
                              }`}
                            >
                              {claim.duplicate_risk_percentage}% risk
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="claims-table__status">
                        <StatusBadge
                          status={claim.financeStatus || (claim.status === "PAID" ? "PAID" : "FINANCE_PENDING")}
                        />
                      </td>
                      <td className="text-right">
                        <button
                          id={`btn-review-${claim.id}`}
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
  );
}
