// MyClaims — full paginated list of all staff claims with filter tabs.

import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { PlusCircle } from "lucide-react";
import ClaimTable from "../../components/claims/ClaimTable";
import { getMyClaims } from "../../services/api";

export default function MyClaims() {
  const navigate = useNavigate();
  const [claims, setClaims] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeFilter, setActiveFilter] = useState("ALL");

  useEffect(() => {
    getMyClaims().then((data) => {
      setClaims(data);
      setLoading(false);
    });
  }, []);

  return (
    <div className="page-content">
      <div className="page-header">
        <div>
          <h1 className="page-header__title">My Claims</h1>
          <p className="page-header__subtitle">
            All your expense claims in one place.
          </p>
        </div>
        <button
          id="my-claims-add-btn"
          className="btn btn--primary"
          onClick={() => navigate("/add-expense")}
        >
          <PlusCircle size={16} strokeWidth={2} />
          Add Expense
        </button>
      </div>

      <div className="section">
        {loading ? (
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
