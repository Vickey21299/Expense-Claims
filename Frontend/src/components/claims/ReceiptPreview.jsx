// ReceiptPreview — shows the receipt image if available, or a styled placeholder.
// receiptUrl will come from the backend in Phase 2.

import { FileText, ImageOff } from "lucide-react";

export default function ReceiptPreview({ receiptUrl, merchant }) {
  return (
    <div className="receipt-preview">
      <h3 className="receipt-preview__title">Receipt</h3>
      {receiptUrl ? (
        <div className="receipt-preview__image-wrap">
          <img
            src={receiptUrl}
            alt={`Receipt for ${merchant || "expense"}`}
            className="receipt-preview__image"
          />
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
