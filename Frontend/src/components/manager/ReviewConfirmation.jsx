// ReviewConfirmation — modal dialog for manager approve/confirm_context/reject.
// mode="approve": shows summary + optional comment field
// mode="confirm_context": shows required context justification for FLAGGED claims
// mode="reject": shows required rejection reason field

import { useState } from "react";
import { Check, AlertTriangle, ShieldCheck, Loader2 } from "lucide-react";

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
  const isConfirmContext = mode === "confirm_context";
  const isReject = mode === "reject";

  let title = "Approve Claim?";
  let subtitle = "You are confirming that this expense is legitimate and valid for business reimbursement.";
  let placeholder = "Add an optional comment…";
  let label = "Comment (optional)";
  let isRequired = false;

  if (isConfirmContext) {
    title = "Confirm Business Context";
    subtitle = "This claim was flagged for potential duplicate or policy anomaly. Please provide a clear business justification to forward it to Finance.";
    placeholder = "e.g. Verified with employee: separate legitimate travel leg for project sprint…";
    label = "Business Justification";
    isRequired = true;
  } else if (isReject) {
    title = "Reject Claim?";
    subtitle = "Please provide a clear reason for rejecting this claim.";
    placeholder = "Enter the reason for rejection…";
    label = "Rejection Reason";
    isRequired = true;
  }

  function handleConfirm() {
    if (isRequired && !comment.trim()) {
      setError(isConfirmContext ? "Business justification is required" : "Rejection reason is required");
      return;
    }
    setError("");
    onConfirm(comment.trim());
  }

  return (
    <div className="modal-overlay" onClick={onCancel}>
      <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className={`modal-icon ${isApprove ? "modal-icon--approve" : isConfirmContext ? "modal-icon--warning" : "modal-icon--reject"}`}>
            {isApprove && <Check size={22} strokeWidth={2.5} />}
            {isConfirmContext && <ShieldCheck size={22} strokeWidth={2.5} />}
            {isReject && <AlertTriangle size={22} strokeWidth={2} />}
          </div>
          <h2 className="modal-title">{title}</h2>
          <p className="modal-subtitle">{subtitle}</p>
        </div>

        {claim && (
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
            {isConfirmContext && claim.duplicate_risk_percentage != null && (
              <div className="modal-summary__row">
                <span className="modal-summary__label">AI Risk Level</span>
                <span className="modal-summary__value" style={{ color: "var(--warning, #f59e0b)", fontWeight: 600 }}>
                  {claim.risk_classification || "FLAGGED"} ({claim.duplicate_risk_percentage}% risk)
                </span>
              </div>
            )}
          </div>
        )}

        <div className="modal-field">
          <label className="modal-field__label">
            {label} {isRequired && <span className="required">*</span>}
          </label>
          <textarea
            className={`modal-field__textarea ${error ? "modal-field__textarea--error" : ""}`}
            placeholder={placeholder}
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
            className={`btn ${isApprove ? "btn--primary" : isConfirmContext ? "btn--warning" : "btn--danger"}`}
            onClick={handleConfirm}
            disabled={loading}
          >
            {loading ? (
              <>
                <Loader2 size={15} className="spin" />
                {isApprove ? "Approving…" : isConfirmContext ? "Confirming…" : "Rejecting…"}
              </>
            ) : (
              isApprove ? "Confirm Approval" : isConfirmContext ? "Confirm & Forward to Finance" : "Reject Claim"
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
