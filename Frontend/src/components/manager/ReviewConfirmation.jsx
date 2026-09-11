// ReviewConfirmation — modal dialog for manager approve/reject confirmation.
// mode="approve": shows summary + optional comment field
// mode="reject": shows required reason field

import { useState } from "react";
import { Check, X, Loader2, AlertTriangle } from "lucide-react";

function formatAmount(amount, currency = "INR") {
  if (!amount && amount !== 0) return "—";
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(amount);
}

export default function ReviewConfirmation({ mode, claim, onConfirm, onCancel, loading = false }) {
  const [comment, setComment] = useState("");
  const [error, setError] = useState("");

  const isApprove = mode === "approve";
  const title = isApprove ? "Approve Claim?" : "Reject Claim?";
  const subtitle = isApprove
    ? "You are confirming that this expense is legitimate and valid for business reimbursement."
    : "Please provide a reason for rejecting this claim.";

  function handleConfirm() {
    if (!isApprove && !comment.trim()) {
      setError("Rejection reason is required");
      return;
    }
    setError("");
    onConfirm(comment.trim());
  }

  return (
    <div className="modal-overlay" onClick={onCancel}>
      <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className={`modal-icon ${isApprove ? "modal-icon--approve" : "modal-icon--reject"}`}>
            {isApprove ? <Check size={22} strokeWidth={2.5} /> : <AlertTriangle size={22} strokeWidth={2} />}
          </div>
          <h2 className="modal-title">{title}</h2>
          <p className="modal-subtitle">{subtitle}</p>
        </div>

        {isApprove && claim && (
          <div className="modal-summary">
            <div className="modal-summary__row">
              <span className="modal-summary__label">Employee</span>
              <span className="modal-summary__value">{claim.employee?.name || "—"}</span>
            </div>
            <div className="modal-summary__row">
              <span className="modal-summary__label">Expense</span>
              <span className="modal-summary__value">
                {claim.merchant} — {formatAmount(claim.amount, claim.currency)}
              </span>
            </div>
          </div>
        )}

        <div className="modal-field">
          <label className="modal-field__label">
            {isApprove ? "Comment (optional)" : "Reason"} {!isApprove && <span className="required">*</span>}
          </label>
          <textarea
            className={`modal-field__textarea ${error ? "modal-field__textarea--error" : ""}`}
            placeholder={isApprove ? "Add an optional comment…" : "Enter the reason for rejection…"}
            rows={3}
            value={comment}
            onChange={(e) => { setComment(e.target.value); if (error) setError(""); }}
          />
          {error && <p className="modal-field__error">{error}</p>}
        </div>

        <div className="modal-actions">
          <button
            className="btn btn--ghost"
            onClick={onCancel}
            disabled={loading}
          >
            Cancel
          </button>
          <button
            className={`btn ${isApprove ? "btn--primary" : "btn--danger"}`}
            onClick={handleConfirm}
            disabled={loading}
          >
            {loading ? (
              <>
                <Loader2 size={15} className="spin" />
                {isApprove ? "Approving…" : "Rejecting…"}
              </>
            ) : (
              isApprove ? "Confirm Approval" : "Reject Claim"
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
