// ClaimTable — renders a filterable list of claims.
// Staff can click a row to view details.
// No approve/reject/pay actions are shown.

import { useNavigate } from "react-router-dom";
import StatusBadge from "../common/StatusBadge";

const FILTERS = [
  { key: "ALL", label: "All" },
  { key: "PENDING", label: "Pending" },
  { key: "APPROVED", label: "Approved" },
  { key: "PAID", label: "Paid" },
  { key: "REJECTED", label: "Rejected" },
];

// Map filter keys to actual status values
const FILTER_STATUS_MAP = {
  ALL: null,
  PENDING: ["SUBMITTED", "UNDER_REVIEW", "FLAGGED", "READY_FOR_PAYMENT"],
  APPROVED: ["APPROVED"],
  PAID: ["PAID"],
  REJECTED: ["REJECTED"],
};

function formatDate(dateStr) {
  if (!dateStr) return "—";
  const d = new Date(dateStr);
  return d.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
}

function formatAmount(amount, currency = "INR") {
  if (!amount && amount !== 0) return "—";
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(amount);
}

export default function ClaimTable({ claims = [], activeFilter, onFilterChange, showFilterBar = true }) {
  const navigate = useNavigate();

  const filtered =
    !activeFilter || activeFilter === "ALL" || !FILTER_STATUS_MAP[activeFilter]
      ? claims
      : claims.filter((c) => FILTER_STATUS_MAP[activeFilter].includes(c.status));

  return (
    <div className="claim-table-wrap">
      {showFilterBar && (
        <div className="filter-bar" role="tablist" aria-label="Filter claims by status">
          {FILTERS.map((f) => (
            <button
              key={f.key}
              role="tab"
              aria-selected={activeFilter === f.key}
              className={`filter-tab ${activeFilter === f.key ? "filter-tab--active" : ""}`}
              onClick={() => onFilterChange(f.key)}
              id={`filter-tab-${f.key.toLowerCase()}`}
            >
              {f.label}
            </button>
          ))}
        </div>
      )}

      {filtered.length === 0 ? (
        <div className="empty-state">
          <p className="empty-state__text">No claims found for this filter.</p>
        </div>
      ) : (
        <div className="table-container">
          <table className="claims-table" aria-label="My expense claims">
            <thead>
              <tr>
                <th>Date</th>
                <th>Merchant</th>
                <th>Category</th>
                <th className="text-right">Amount</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((claim) => (
                <tr
                  key={claim.id}
                  className="claims-table__row"
                  onClick={() => navigate(`/claims/${claim.id}`)}
                  role="button"
                  tabIndex={0}
                  aria-label={`View claim from ${claim.merchant}`}
                  onKeyDown={(e) => e.key === "Enter" && navigate(`/claims/${claim.id}`)}
                >
                  <td className="claims-table__date">{formatDate(claim.date)}</td>
                  <td className="claims-table__merchant">
                    <span className="merchant-name">{claim.merchant || <span className="text-muted">Draft</span>}</span>
                    <span className="claim-id">{claim.id}</span>
                  </td>
                  <td className="claims-table__category">{claim.category || "—"}</td>
                  <td className="claims-table__amount text-right">
                    {claim.amount ? formatAmount(claim.amount, claim.currency) : "—"}
                  </td>
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
  );
}
