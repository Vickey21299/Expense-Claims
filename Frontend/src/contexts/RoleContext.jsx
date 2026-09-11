import { createContext, useState, useEffect, useContext } from "react";

export const RoleContext = createContext();

export function RoleProvider({ children }) {
  const [role, setRole] = useState(() => {
    return localStorage.getItem("expense_app_role") || "staff";
  });

  useEffect(() => {
    localStorage.setItem("expense_app_role", role);
  }, [role]);

  return (
    <RoleContext.Provider value={{ role, setRole }}>
      {children}
    </RoleContext.Provider>
  );
}

export function useRole() {
  return useContext(RoleContext);
}
