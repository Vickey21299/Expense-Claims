// ClaimDetails — full detail view for a single claim.
// Staff can view details, history, and receipt — but cannot change status.

import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { ArrowLeft, User, Calendar, Tag, FileText, DollarSign, Building2, Clock } from "lucide-react";
import StatusBadge from "../../components/common/StatusBadge";
import ClaimHistory from "../../components/claims/ClaimHistory";
import ReceiptPreview from "../../components/claims/ReceiptPreview";
import { getClaim } from "../../services/api";

function formatDate(dateStr) {
  if (!dateStr) return "—";
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return "—";
  return d.toLocaleDateString("en-IN", {
    day: "2-digit",
    month: "long",
    year: "numeric",
  });
}

function formatTime(dateStr) {
  if (!dateStr) return "";
  if (typeof dateStr === "string" && !dateStr.includes("T") && !dateStr.includes(":")) {
    return "";
  }
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return "";
  return d.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", hour12: true });
}

function formatAmount(amount, currency = "INR") {
  if (!amount && amount !== 0) return "—";
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(amount);
}

function DetailRow({ icon: Icon, label, value }) {
  return (
    <div className="detail-row">
      <div className="detail-row__icon">
        <Icon size={15} strokeWidth={1.75} />
      </div>
      <div className="detail-row__body">
        <p className="detail-row__label">{label}</p>
        <p className="detail-row__value">{value || "—"}</p>
      </div>
    </div>
  );
}

export default function ClaimDetails() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [claim, setClaim] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(true);
    getClaim(id)
      .then((data) => {
        setClaim(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, [id]);

  if (loading) {
    return (
      <div className="page-content">
        <div className="loading-state">
          <div className="spinner" />
          <p>Loading claim…</p>
        </div>
      </div>
    );
  }

  if (error || !claim) {
    return (
      <div className="page-content">
        <div className="error-state">
          <p>Claim not found.</p>
          <button className="btn btn--ghost" onClick={() => navigate("/claims")}>
            Back to My Claims
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="page-content">
      {/* Back navigation */}
      <button
        id="claim-details-back-btn"
        className="btn btn--ghost btn--sm back-btn"
        onClick={() => navigate(-1)}
      >
        <ArrowLeft size={15} strokeWidth={2} />
        Back
      </button>

      {/* Page header */}
      <div className="page-header page-header--compact">
        <div>
          <div className="page-header__meta">
            <span className="claim-id-label">{claim.claimRef || claim.claim_ref || claim.id}</span>
            <StatusBadge status={claim.status} />
          </div>
          <h1 className="page-header__title">
            {claim.merchant || "Draft Claim"}
          </h1>
          <p className="page-header__subtitle">
            {claim.category || claim.claim_type} · Expense Date: {formatDate(claim.claim_date || claim.date)} · Initiated: {formatDate(claim.createdAt || claim.created_at || claim.submittedAt || claim.submitted_at)}
          </p>
        </div>

        <div className="claim-amount-hero">
          <p className="claim-amount-hero__label">Amount</p>
          <p className="claim-amount-hero__value">
            {formatAmount(claim.amount, claim.currency)}
          </p>
        </div>
      </div>

      {/* Two-column layout */}
      <div className="detail-grid">
        {/* Left column */}
        <div className="detail-col">
          {/* Expense section */}
          <div className="card">
            <h2 className="card__title">Expense Details</h2>
            <div className="detail-rows">
              <DetailRow icon={Building2} label="Merchant" value={claim.merchant} />
              <DetailRow icon={DollarSign} label="Amount" value={formatAmount(claim.amount, claim.currency)} />
              <DetailRow icon={Tag} label="Category" value={claim.category || claim.claim_type} />
              <DetailRow icon={Calendar} label="Expense Date" value={formatDate(claim.claim_date || claim.date)} />
              <DetailRow
                icon={Clock}
                label="Claim Initiated"
                value={
                  claim.createdAt || claim.created_at || claim.submittedAt || claim.submitted_at
                    ? `${formatDate(claim.createdAt || claim.created_at || claim.submittedAt || claim.submitted_at)}${
                        formatTime(claim.createdAt || claim.created_at || claim.submittedAt || claim.submitted_at)
                          ? ` at ${formatTime(claim.createdAt || claim.created_at || claim.submittedAt || claim.submitted_at)}`
                          : ""
                      }`
                    : "—"
                }
              />
              {claim.description && (
                <DetailRow icon={FileText} label="Description" value={claim.description} />
              )}
              {claim.paymentReference && (
                <DetailRow icon={DollarSign} label="Payment Reference" value={claim.paymentReference} />
              )}
            </div>
          </div>

          {/* Verification Audit Summary if available */}
          {(claim.verificationStatus || (claim.verificationResults && claim.verificationResults.length > 0)) && (
            <div className="card">
              <h2 className="card__title">System Verification</h2>
              <div style={{ display: "flex", flexDirection: "column", gap: "8px", marginTop: "12px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontSize: "13px", color: "var(--text-muted)" }}>Verification Status:</span>
                  <span style={{
                    fontSize: "12px",
                    fontWeight: 600,
                    padding: "3px 8px",
                    borderRadius: "4px",
                    background: claim.verificationStatus === "CLEAN" ? "rgba(16, 185, 129, 0.15)" : "rgba(245, 158, 11, 0.15)",
                    color: claim.verificationStatus === "CLEAN" ? "#059669" : "#d97706",
                  }}>
                    {claim.verificationStatus || "CLEAN"}
                  </span>
                </div>
                {claim.verificationResults && claim.verificationResults.length > 0 && (
                  <p style={{ fontSize: "13px", color: "var(--text-h)", background: "var(--surface-2)", padding: "10px", borderRadius: "6px", margin: "4px 0 0" }}>
                    {claim.verificationResults[0].message || "Claim passed deterministic verification checks."}
                  </p>
                )}
              </div>
            </div>
          )}

          {/* Manager section */}
          <div className="card">
            <h2 className="card__title">Assigned Manager & Review Context</h2>
            <div className="manager-row">
              <div className="manager-avatar" aria-hidden="true">
                {claim.manager?.charAt(0) || "M"}
              </div>
              <div>
                <p className="manager-name">{claim.manager || "Rahul Sharma"}</p>
                <p className="manager-meta">Reviewing manager</p>
              </div>
            </div>

            {claim.manager_comment && (
              <div className="history-comment-box history-comment-box--manager" style={{ marginTop: "12px" }}>
                <div className="history-comment-header">
                  <span>Manager Justification Comment</span>
                </div>
                <p className="history-comment-text">"{claim.manager_comment}"</p>
              </div>
            )}

            {claim.finance_comment && (
              <div className="history-comment-box history-comment-box--finance" style={{ marginTop: "10px" }}>
                <div className="history-comment-header">
                  <span>Finance Verification Note</span>
                </div>
                <p className="history-comment-text">"{claim.finance_comment}"</p>
              </div>
            )}
          </div>

          {/* History */}
          <div className="card">
            <ClaimHistory history={claim.history || []} claim={claim} />
          </div>
        </div>

        {/* Right column */}
        <div className="detail-col">
          <div className="card">
            <ReceiptPreview receiptUrl={claim.receiptUrl} merchant={claim.merchant} />
          </div>
        </div>
      </div>
    </div>
  );
}
