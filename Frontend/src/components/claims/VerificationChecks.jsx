// VerificationChecks — shows automated verification results for a claim.
// Green checkmarks for passed checks, amber warnings for failed/flagged checks.

import { CheckCircle2, AlertTriangle } from "lucide-react";

export default function VerificationChecks({ checks = [] }) {
  if (!checks || checks.length === 0) return null;

  const hasFailed = checks.some((c) => !c.passed);

  return (
    <div className="verification-checks">
      <h3 className="verification-checks__title">Verification</h3>
      {hasFailed ? (
        <div className="verification-checks__warning">
          <AlertTriangle size={16} strokeWidth={2} />
          <span>Attention Required</span>
        </div>
      ) : null}
      <ul className="verification-checks__list">
        {checks.map((check, i) => (
          <li
            key={i}
            className={`verification-checks__item ${check.passed ? "verification-checks__item--pass" : "verification-checks__item--fail"}`}
          >
            {check.passed ? (
              <CheckCircle2 size={16} strokeWidth={2} />
            ) : (
              <AlertTriangle size={16} strokeWidth={2} />
            )}
            <div>
              <span className="verification-checks__text">{check.check}</span>
              {check.message && (
                <span className="verification-checks__message">{check.message}</span>
              )}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
