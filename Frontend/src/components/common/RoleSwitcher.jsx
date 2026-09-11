import { useRole } from "../../contexts/RoleContext";
import { useNavigate } from "react-router-dom";
import { Users } from "lucide-react";

export default function RoleSwitcher() {
  const { role, setRole } = useRole();
  const navigate = useNavigate();

  const handleRoleChange = (e) => {
    const newRole = e.target.value;
    setRole(newRole);
    // Redirect to the default route for the new role
    if (newRole === "staff") {
      navigate("/");
    } else if (newRole === "manager") {
      navigate("/manager");
    } else if (newRole === "finance") {
      navigate("/finance");
    }
  };

  return (
    <div style={{ padding: "16px", borderTop: "1px solid var(--border)", marginTop: "auto" }}>
      <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "8px" }}>
        <Users size={16} className="text-muted" />
        <label htmlFor="role-switcher" style={{ fontSize: "12px", fontWeight: "600", color: "var(--text-sm)", textTransform: "uppercase" }}>
          Switch Role
        </label>
      </div>
      <select
        id="role-switcher"
        className="form-select"
        style={{ width: "100%", fontSize: "13px", padding: "8px 12px" }}
        value={role}
        onChange={handleRoleChange}
      >
        <option value="staff">Staff</option>
        <option value="manager">Manager</option>
        <option value="finance">Finance</option>
      </select>
    </div>
  );
}
