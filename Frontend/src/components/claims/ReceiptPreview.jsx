// ReceiptPreview — shows the receipt image if available, or a styled placeholder.
// receiptUrl will come from the backend in Phase 2.

import { FileText, ImageOff } from "lucide-react";

export default function ReceiptPreview({ receiptUrl, merchant }) {
  return (
    <div className="receipt-preview">
      <h3 className="receipt-preview__title">Receipt</h3>
      {receiptUrl ? (
        <div className="receipt-preview__image-wrap">
          {receiptUrl.toLowerCase().includes(".pdf") ? (
            <div style={{ padding: "28px 16px", textAlign: "center", background: "var(--surface-2)", borderRadius: "var(--radius)", border: "1px solid var(--border)" }}>
              <FileText size={44} color="var(--accent)" style={{ margin: "0 auto 12px" }} />
              <p style={{ fontSize: "14px", fontWeight: 600, color: "var(--text-h)", marginBottom: "8px" }}>PDF Receipt</p>
              <a href={receiptUrl} target="_blank" rel="noopener noreferrer" className="btn btn--secondary btn--sm">
                Open / Download Document ↗
              </a>
            </div>
          ) : (
            <img
              src={receiptUrl}
              alt={`Receipt for ${merchant || "expense"}`}
              className="receipt-preview__image"
            />
          )}
          <div style={{ marginTop: "10px", textAlign: "center" }}>
            <a href={receiptUrl} target="_blank" rel="noopener noreferrer" style={{ fontSize: "12px", color: "var(--accent)", fontWeight: 500, textDecoration: "underline" }}>
              View full file in new tab ↗
            </a>
          </div>
        </div>
      ) : (
        <div className="receipt-preview__placeholder">
          <div className="receipt-preview__placeholder-icon">
            <FileText size={40} strokeWidth={1.25} />
          </div>
          <p className="receipt-preview__placeholder-title">No receipt attached</p>
          <p className="receipt-preview__placeholder-subtitle">
            Receipt will appear here once uploaded.
          </p>

          {/* Mock receipt visual — a paper-style block */}
          <div className="receipt-mock">
            <div className="receipt-mock__header">
              <span className="receipt-mock__store">{merchant || "Merchant"}</span>
            </div>
            <div className="receipt-mock__lines">
              <div className="receipt-mock__line receipt-mock__line--long" />
              <div className="receipt-mock__line receipt-mock__line--medium" />
              <div className="receipt-mock__line receipt-mock__line--short" />
              <div className="receipt-mock__line receipt-mock__line--long" />
              <div className="receipt-mock__divider" />
              <div className="receipt-mock__total">
                <div className="receipt-mock__line receipt-mock__line--short" />
                <div className="receipt-mock__line receipt-mock__line--amount" />
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
