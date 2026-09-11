// ClaimDetails — full detail view for a single claim.
// Staff can view details, history, and receipt — but cannot change status.

import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { ArrowLeft, User, Calendar, Tag, FileText, DollarSign, Building2 } from "lucide-react";
import StatusBadge from "../../components/common/StatusBadge";
import ClaimHistory from "../../components/claims/ClaimHistory";
import ReceiptPreview from "../../components/claims/ReceiptPreview";
import { getClaim } from "../../services/api";

function formatDate(dateStr) {
  if (!dateStr) return "—";
  return new Date(dateStr).toLocaleDateString("en-IN", {
    day: "2-digit",
    month: "long",
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
            <span className="claim-id-label">{claim.id}</span>
            <StatusBadge status={claim.status} />
          </div>
          <h1 className="page-header__title">
            {claim.merchant || "Draft Claim"}
          </h1>
          <p className="page-header__subtitle">
            {claim.category} · {formatDate(claim.date)}
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
              <DetailRow icon={Tag} label="Category" value={claim.category} />
              <DetailRow icon={Calendar} label="Date" value={formatDate(claim.date)} />
              {claim.description && (
                <DetailRow icon={FileText} label="Description" value={claim.description} />
              )}
            </div>
          </div>

          {/* Manager section */}
          <div className="card">
            <h2 className="card__title">Assigned Manager</h2>
            <div className="manager-row">
              <div className="manager-avatar" aria-hidden="true">
                {claim.manager?.charAt(0) || "M"}
              </div>
              <div>
                <p className="manager-name">{claim.manager || "—"}</p>
                <p className="manager-meta">Reviewing this claim</p>
              </div>
            </div>
          </div>

          {/* History */}
          <div className="card">
            <ClaimHistory history={claim.history || []} />
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
