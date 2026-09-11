// ManagerClaimReview — full detail view for manager to review and decide on a claim.
// Shows expense info, employee info, verification, duplicate alert, receipt, history.
// Manager can approve or reject (with confirmation modal).
// Self-claim protection: cannot approve/reject own claims.

import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  ArrowLeft, User, Calendar, Tag, FileText, DollarSign,
  Building2, Briefcase, CheckCircle2, XCircle, ShieldAlert,
} from "lucide-react";
import StatusBadge from "../../components/common/StatusBadge";
import ClaimHistory from "../../components/claims/ClaimHistory";
import ReceiptPreview from "../../components/claims/ReceiptPreview";
import DuplicateAlert from "../../components/claims/DuplicateAlert";
import VerificationChecks from "../../components/claims/VerificationChecks";
import ReviewConfirmation from "../../components/manager/ReviewConfirmation";
import { getManagerClaim, approveClaim, rejectClaim } from "../../services/api";
import { CURRENT_MANAGER } from "../../data/mockClaims";

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

const REVIEWABLE_STATUSES = ["SUBMITTED", "UNDER_REVIEW", "FLAGGED"];

export default function ManagerClaimReview() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [claim, setClaim] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [modal, setModal] = useState(null); // "approve" | "reject" | null
  const [actionLoading, setActionLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    getManagerClaim(id)
      .then((data) => {
        setClaim(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, [id]);

  // Self-claim check
  const isSelfClaim = claim?.employee?.id === CURRENT_MANAGER.id;
  const canReview = !isSelfClaim && REVIEWABLE_STATUSES.includes(claim?.status);

  async function handleApprove(comment) {
    setActionLoading(true);
    try {
      const updated = await approveClaim(id, comment);
      setClaim(updated);
      setModal(null);
    } catch (err) {
      console.error("Approve failed:", err);
    }
    setActionLoading(false);
  }

  async function handleReject(reason) {
    setActionLoading(true);
    try {
      const updated = await rejectClaim(id, reason);
      setClaim(updated);
      setModal(null);
    } catch (err) {
      console.error("Reject failed:", err);
    }
    setActionLoading(false);
  }

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
          <button className="btn btn--ghost" onClick={() => navigate("/manager/claims")}>
            Back to Team Claims
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="page-content">
      {/* Back */}
      <button
        id="mgr-review-back-btn"
        className="btn btn--ghost btn--sm back-btn"
        onClick={() => navigate("/manager/claims")}
      >
        <ArrowLeft size={15} strokeWidth={2} />
        Back to Team Claims
      </button>

      {/* Header */}
      <div className="page-header page-header--compact">
        <div>
          <div className="page-header__meta">
            <span className="claim-id-label">{claim.id}</span>
            <StatusBadge status={claim.status} />
            {claim.duplicate?.flagged && (
              <StatusBadge status="FLAGGED" />
            )}
          </div>
          <h1 className="page-header__title">
            {claim.merchant || "Claim Review"}
          </h1>
          <p className="page-header__subtitle">
            {claim.employee?.name} · {claim.category} · {formatDate(claim.date)}
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
          {/* Expense Details */}
          <div className="card">
            <h2 className="card__title">Expense Information</h2>
            <div className="detail-rows">
              <DetailRow icon={Building2} label="Merchant" value={claim.merchant} />
              <DetailRow icon={DollarSign} label="Amount" value={formatAmount(claim.amount, claim.currency)} />
              <DetailRow icon={Tag} label="Category" value={claim.category} />
              <DetailRow icon={Calendar} label="Expense Date" value={formatDate(claim.date)} />
              {claim.description && (
                <DetailRow icon={FileText} label="Description" value={claim.description} />
              )}
            </div>
          </div>

          {/* Employee Information */}
          <div className="card">
            <h2 className="card__title">Employee</h2>
            <div className="manager-row" style={{ marginBottom: "12px" }}>
              <div className="manager-avatar" aria-hidden="true">
                {claim.employee?.name?.charAt(0) || "E"}
              </div>
              <div>
                <p className="manager-name">{claim.employee?.name || "—"}</p>
                <p className="manager-meta">
                  {claim.employee?.department} · {claim.employee?.role}
                </p>
              </div>
            </div>
            <div className="detail-rows" style={{ borderTop: "1px solid var(--border)", paddingTop: "12px" }}>
              <DetailRow
                icon={User}
                label="Manager"
                value={claim.manager?.id === CURRENT_MANAGER.id ? "You" : claim.manager?.name}
              />
            </div>
          </div>

          {/* Verification */}
          {claim.verification && claim.verification.length > 0 && (
            <div className="card">
              <VerificationChecks checks={claim.verification} />
            </div>
          )}

          {/* Duplicate Alert */}
          {claim.duplicate?.flagged && (
            <div className="card">
              <DuplicateAlert duplicate={claim.duplicate} />
            </div>
          )}

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

          {/* Manager Decision Panel */}
          <div className="card review-decision">
            <h2 className="card__title">Manager Decision</h2>

            {/* Already decided */}
            {claim.status === "APPROVED" && (
              <div className="review-decision__result review-decision__result--approved">
                <CheckCircle2 size={18} strokeWidth={2} />
                <div>
                  <p className="review-decision__status">Approved</p>
                  {claim.reviewComment && (
                    <p className="review-decision__comment">"{claim.reviewComment}"</p>
                  )}
                </div>
              </div>
            )}

            {claim.status === "REJECTED" && (
              <div className="review-decision__result review-decision__result--rejected">
                <XCircle size={18} strokeWidth={2} />
                <div>
                  <p className="review-decision__status">Rejected</p>
                  {claim.reviewComment && (
                    <p className="review-decision__comment">"{claim.reviewComment}"</p>
                  )}
                </div>
              </div>
            )}

            {claim.status === "PAID" && (
              <div className="review-decision__result review-decision__result--approved">
                <CheckCircle2 size={18} strokeWidth={2} />
                <div>
                  <p className="review-decision__status">Approved & Paid</p>
                  {claim.reviewComment && (
                    <p className="review-decision__comment">"{claim.reviewComment}"</p>
                  )}
                </div>
              </div>
            )}

            {/* Self-claim warning */}
            {isSelfClaim && REVIEWABLE_STATUSES.includes(claim.status) && (
              <div className="review-decision__self-claim">
                <ShieldAlert size={18} strokeWidth={2} />
                <p>This claim requires review by your manager.</p>
              </div>
            )}

            {/* Action buttons */}
            {canReview && (
              <div className="review-decision__actions">
                <button
                  id="mgr-reject-btn"
                  className="btn btn--danger"
                  onClick={() => setModal("reject")}
                >
                  <XCircle size={15} strokeWidth={2} />
                  Reject
                </button>
                <button
                  id="mgr-approve-btn"
                  className="btn btn--primary"
                  onClick={() => setModal("approve")}
                >
                  <CheckCircle2 size={15} strokeWidth={2} />
                  Approve
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Confirmation modal */}
      {modal && (
        <ReviewConfirmation
          mode={modal}
          claim={claim}
          onConfirm={modal === "approve" ? handleApprove : handleReject}
          onCancel={() => setModal(null)}
          loading={actionLoading}
        />
      )}
    </div>
  );
}
