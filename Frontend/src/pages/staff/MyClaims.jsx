import { useState, useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { PlusCircle, AlertCircle, RefreshCw, CheckCircle2 } from "lucide-react";
import ClaimTable from "../../components/claims/ClaimTable";
import { getMyClaims } from "../../services/api";

export default function MyClaims() {
  const navigate = useNavigate();
  const location = useLocation();
  const [claims, setClaims] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [toast, setToast] = useState(location.state?.toast || null);
  const [activeFilter, setActiveFilter] = useState("ALL");

  const fetchClaims = () => {
    setLoading(true);
    setError(null);
    getMyClaims()
      .then((data) => {
        setClaims(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message || "Failed to fetch claims from server");
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchClaims();
    if (location.state?.toast) {
      const timer = setTimeout(() => setToast(null), 4000);
      return () => clearTimeout(timer);
    }
  }, [location.state]);

  return (
    <div className="page-content">
      {toast && (
        <div className="toast-notification" style={{
          marginBottom: "16px",
          padding: "12px 16px",
          borderRadius: "8px",
          background: "rgba(16, 185, 129, 0.12)",
          border: "1px solid rgba(16, 185, 129, 0.3)",
          color: "#059669",
          display: "flex",
          alignItems: "center",
          gap: "8px",
          fontSize: "14px",
          fontWeight: 500,
        }}>
          <CheckCircle2 size={18} />
          <span>{toast}</span>
        </div>
      )}

      <div className="page-header">
        <div>
          <h1 className="page-header__title">My Claims</h1>
          <p className="page-header__subtitle">
            All your expense claims in one place.
          </p>
        </div>
        <div style={{ display: "flex", gap: "10px" }}>
          <button
            className="btn btn--ghost btn--sm"
            onClick={fetchClaims}
            disabled={loading}
            title="Refresh claims"
          >
            <RefreshCw size={14} className={loading ? "spin" : ""} />
            Refresh
          </button>
          <button
            id="my-claims-add-btn"
            className="btn btn--primary"
            onClick={() => navigate("/add-expense")}
          >
            <PlusCircle size={16} strokeWidth={2} />
            Add Expense
          </button>
        </div>
      </div>

      <div className="section">
        {error ? (
          <div className="error-state" style={{ padding: "32px", textAlign: "center" }}>
            <AlertCircle size={36} color="var(--danger)" style={{ margin: "0 auto 12px" }} />
            <p style={{ color: "var(--text-h)", fontWeight: 600, marginBottom: "8px" }}>Could not load claims</p>
            <p style={{ color: "var(--text-muted)", fontSize: "14px", marginBottom: "16px" }}>{error}</p>
            <button className="btn btn--secondary btn--sm" onClick={fetchClaims}>
              Try Again
            </button>
          </div>
        ) : loading ? (
          <div className="table-skeleton">
            {[1, 2, 3, 4, 5].map((n) => (
              <div key={n} className="table-skeleton__row skeleton" />
            ))}
          </div>
        ) : (
          <ClaimTable
            claims={claims}
            activeFilter={activeFilter}
            onFilterChange={setActiveFilter}
            showFilterBar={true}
          />
        )}
      </div>
    </div>
  );
}
