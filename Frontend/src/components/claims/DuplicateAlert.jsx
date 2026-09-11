// DuplicateAlert — displays duplicate warning for flagged claims.
// Manager can see the evidence but CANNOT clear or confirm duplicates (Finance-only).

import { AlertTriangle } from "lucide-react";

export default function DuplicateAlert({ duplicate }) {
  if (!duplicate || !duplicate.flagged) return null;

  return (
    <div className="duplicate-alert">
      <div className="duplicate-alert__header">
        <AlertTriangle size={18} strokeWidth={2} />
        <h3 className="duplicate-alert__title">Possible Duplicate</h3>
      </div>
      <p className="duplicate-alert__desc">
        This claim appears similar to another submitted claim.
      </p>

      {duplicate.matchedClaimId && (
        <div className="duplicate-alert__match">
          <span className="duplicate-alert__label">Matched claim</span>
          <span className="duplicate-alert__value">{duplicate.matchedClaimId}</span>
        </div>
      )}

      {duplicate.signals && duplicate.signals.length > 0 && (
        <div className="duplicate-alert__section">
          <span className="duplicate-alert__label">Matching signals</span>
          <ul className="duplicate-alert__signals">
            {duplicate.signals.map((signal, i) => (
              <li key={i}>{signal}</li>
            ))}
          </ul>
        </div>
      )}

      {duplicate.assessment && (
        <div className="duplicate-alert__match">
          <span className="duplicate-alert__label">AI Assessment</span>
          <span className="duplicate-alert__assessment">{duplicate.assessment}</span>
        </div>
      )}
    </div>
  );
}
