// ManagerClaims — full team claims list with filters and search.
// Manager can filter by status and search by employee name or merchant.

import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Search } from "lucide-react";
import StatusBadge from "../../components/common/StatusBadge";
import { getManagerClaims } from "../../services/api";

const FILTERS = [
  { key: "ALL", label: "All" },
  { key: "PENDING", label: "Pending Review" },
  { key: "APPROVED", label: "Approved" },
  { key: "REJECTED", label: "Rejected" },
  { key: "FLAGGED", label: "Flagged" },
];

const FILTER_MAP = {
  ALL: null,
  PENDING: ["SUBMITTED", "UNDER_REVIEW"],
  APPROVED: ["APPROVED"],
  REJECTED: ["REJECTED"],
  FLAGGED: ["FLAGGED"],
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
  const [filter, setFilter] = useState("ALL");
  const [search, setSearch] = useState("");

  useEffect(() => {
    getManagerClaims().then((data) => {
      setClaims(data);
      setLoading(false);
    });
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
        (c.merchant || "").toLowerCase().includes(q)
    );
  }

  if (loading) {
    return (
      <div className="page-content">
        <div className="loading-state">
          <div className="spinner" />
          <p>Loading claims…</p>
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
            Review reimbursement claims submitted by your team.
          </p>
        </div>
      </div>

      {/* Search */}
      <div className="search-bar">
        <Search size={16} strokeWidth={2} className="search-bar__icon" />
        <input
          id="mgr-search-input"
          type="text"
          className="search-bar__input"
          placeholder="Search employee or merchant…"
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
            <p className="empty-state__text">No claims found for this filter.</p>
          </div>
        ) : (
          <div className="table-container">
            <table className="claims-table" aria-label="Team claims">
              <thead>
                <tr>
                  <th>Employee</th>
                  <th>Date</th>
                  <th>Merchant</th>
                  <th>Category</th>
                  <th className="text-right">Amount</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((claim) => (
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
                        <span className="claim-id">{claim.employee?.role || ""}</span>
                      </div>
                    </td>
                    <td className="claims-table__date">{formatDate(claim.date)}</td>
                    <td>
                      <div className="claims-table__merchant">
                        <span className="merchant-name">{claim.merchant}</span>
                        <span className="claim-id">{claim.id}</span>
                      </div>
                    </td>
                    <td className="claims-table__category">{claim.category || "—"}</td>
                    <td className="claims-table__amount text-right">
                      {formatAmount(claim.amount, claim.currency)}
                    </td>
                    <td className="claims-table__status">
                      <StatusBadge status={claim.status} />
                    </td>
                    <td>
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
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
