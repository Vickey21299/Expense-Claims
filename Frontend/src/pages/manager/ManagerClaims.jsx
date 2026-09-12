// ManagerClaims — full team claims list with filters and search.
// Manager can filter by status and search by employee name, merchant, or claim reference.

import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Search, ShieldAlert, RefreshCw } from "lucide-react";
import StatusBadge from "../../components/common/StatusBadge";
import { getManagerClaims } from "../../services/api";

const FILTERS = [
  { key: "ALL", label: "All Claims" },
  { key: "PENDING", label: "Pending Review" },
  { key: "FLAGGED", label: "Flagged Anomaly" },
  { key: "APPROVED", label: "Approved / Confirmed" },
  { key: "REJECTED", label: "Rejected" },
];

const FILTER_MAP = {
  ALL: null,
  PENDING: ["SUBMITTED", "UNDER_REVIEW"],
  FLAGGED: ["FLAGGED"],
  APPROVED: ["APPROVED", "MANAGER_CONFIRMED", "READY_FOR_PAYMENT", "PAID"],
  REJECTED: ["REJECTED"],
};

function formatDate(dateStr) {
  if (!dateStr) return "—";
  return new Date(dateStr).toLocaleDateString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

function formatAmount(amount, currency = "INR") {
  if (!amount && amount !== 0) return "—";
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(amount);
}

export default function ManagerClaims() {
  const navigate = useNavigate();
  const [claims, setClaims] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [filter, setFilter] = useState("ALL");
  const [search, setSearch] = useState("");

  const loadClaims = () => {
    setRefreshing(true);
    getManagerClaims()
      .then((data) => {
        setClaims(data);
        setLoading(false);
        setRefreshing(false);
      })
      .catch((err) => {
        console.error("Failed to fetch manager claims:", err);
        setLoading(false);
        setRefreshing(false);
      });
  };

  useEffect(() => {
    loadClaims();
  }, []);

  // Apply filters
  let filtered = claims;
  if (FILTER_MAP[filter]) {
    filtered = filtered.filter((c) => FILTER_MAP[filter].includes(c.status));
  }
  // Apply search
  if (search.trim()) {
    const q = search.toLowerCase();
    filtered = filtered.filter(
      (c) =>
        (c.employee?.name || "").toLowerCase().includes(q) ||
        (c.merchant || "").toLowerCase().includes(q) ||
        (c.claimRef || c.id || "").toLowerCase().includes(q) ||
        (c.category || "").toLowerCase().includes(q)
    );
  }

  if (loading) {
    return (
      <div className="page-content">
        <div className="loading-state">
          <div className="spinner" />
          <p>Loading team claims…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="page-content">
      {/* Header */}
      <div className="page-header">
        <div>
          <h1 className="page-header__title">Team Claims</h1>
          <p className="page-header__subtitle">
            Review and track reimbursement claims submitted across your team.
          </p>
        </div>
        <button
          className="btn btn--ghost btn--sm"
          onClick={loadClaims}
          disabled={refreshing}
          style={{ display: "flex", alignItems: "center", gap: "6px" }}
        >
          <RefreshCw size={14} className={refreshing ? "spin" : ""} />
          {refreshing ? "Refreshing…" : "Refresh"}
        </button>
      </div>

      {/* Search */}
      <div className="search-bar">
        <Search size={16} strokeWidth={2} className="search-bar__icon" />
        <input
          id="mgr-search-input"
          type="text"
          className="search-bar__input"
          placeholder="Search employee, merchant, reference (e.g. CLM-1031), or category…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {/* Table */}
      <div className="claim-table-wrap">
        {/* Filter tabs */}
        <div className="filter-bar" role="tablist" aria-label="Filter claims by status">
          {FILTERS.map((f) => (
            <button
              key={f.key}
              role="tab"
              aria-selected={filter === f.key}
              className={`filter-tab ${filter === f.key ? "filter-tab--active" : ""}`}
              onClick={() => setFilter(f.key)}
              id={`mgr-filter-${f.key.toLowerCase()}`}
            >
              {f.label}
            </button>
          ))}
        </div>

        {filtered.length === 0 ? (
          <div className="empty-state">
            <p className="empty-state__text">No claims found for this filter or search query.</p>
          </div>
        ) : (
          <div className="table-container">
            <table className="claims-table" aria-label="Team claims">
              <thead>
                <tr>
                  <th>Employee</th>
                  <th>Claim Initiated</th>
                  <th>Expense Date</th>
                  <th>Merchant & Ref</th>
                  <th>Category</th>
                  <th className="text-right">Amount</th>
                  <th>Status & Risk</th>
                  <th>Action</th>
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
                      onClick={() => navigate(`/manager/claims/${claim.id}`)}
                      role="button"
                      tabIndex={0}
                      aria-label={`Review claim from ${empName}`}
                      onKeyDown={(e) => e.key === "Enter" && navigate(`/manager/claims/${claim.id}`)}
                    >
                      <td>
                        <div className="employee-row">
                          <div className="employee-avatar-sm" aria-hidden="true">
                            {initials}
                          </div>
                          <div className="claims-table__employee">
                            <span className="employee-name">{empName}</span>
                            <span className="claim-id">{claim.employee?.department || "Engineering"} · {claim.employee?.role || "Staff"}</span>
                          </div>
                        </div>
                      </td>
                      <td className="claims-table__date">{formatDate(claim.submittedAt || claim.createdAt)}</td>
                      <td className="claims-table__date">{formatDate(claim.date || claim.claim_date)}</td>
                      <td className="claims-table__merchant">
                        <span className="merchant-name">{claim.merchant}</span>
                        <span className="claim-id">{claim.claimRef || claim.claim_ref || claim.id}</span>
                      </td>
                      <td className="claims-table__category">{claim.category || "—"}</td>
                      <td className="claims-table__amount text-right">
                        {formatAmount(claim.amount, claim.currency)}
                      </td>
                      <td className="claims-table__status">
                        <div style={{ display: "flex", flexDirection: "column", gap: "4px", alignItems: "flex-start" }}>
                          <StatusBadge status={claim.status} />
                          {claim.duplicate_risk_percentage != null && claim.duplicate_risk_percentage > 30 && (
                            <span
                              className={`claim-risk-pill ${
                                claim.duplicate_risk_percentage >= 70
                                  ? "claim-risk-pill--high"
                                  : "claim-risk-pill--medium"
                              }`}
                            >
                              <ShieldAlert size={11} />
                              {claim.duplicate_risk_percentage}% risk
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="text-right">
                        <button
                          className="btn btn--ghost btn--sm"
                          onClick={(e) => {
                            e.stopPropagation();
                            navigate(`/manager/claims/${claim.id}`);
                          }}
                        >
                          Review
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
