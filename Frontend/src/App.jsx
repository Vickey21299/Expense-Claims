// App.jsx — root router shell.
// Hardcoded role switches between staff and manager.
// Do not implement auth or role switching until Phase 3.

import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import StaffLayout from "./components/layout/StaffLayout";
import StaffDashboard from "./pages/staff/StaffDashboard";
import MyClaims from "./pages/staff/MyClaims";
import ClaimDetails from "./pages/staff/ClaimDetails";
import CreateClaim from "./pages/staff/CreateClaim";
import ManagerLayout from "./components/layout/ManagerLayout";
import ManagerDashboard from "./pages/manager/ManagerDashboard";
import ManagerClaims from "./pages/manager/ManagerClaims";
import ManagerClaimReview from "./pages/manager/ManagerClaimReview";

import FinanceLayout from "./components/layout/FinanceLayout";
import FinanceDashboard from "./pages/finance/FinanceDashboard";
import FinanceVerificationQueue from "./pages/finance/FinanceVerificationQueue";
import FinancePayments from "./pages/finance/FinancePayments";
import FinanceReports from "./pages/finance/FinanceReports";
import FinanceClaimReview from "./pages/finance/FinanceClaimReview";

import { RoleProvider, useRole } from "./contexts/RoleContext";

function AppRoutes() {
  const { role } = useRole();

  if (role === "staff") {
    return (
      <Routes>
        <Route path="/" element={<StaffLayout />}>
          <Route index element={<StaffDashboard />} />
          <Route path="claims" element={<MyClaims />} />
          <Route path="claims/:id" element={<ClaimDetails />} />
          <Route path="add-expense" element={<CreateClaim />} />
          {/* Redirect any unknown staff paths to dashboard */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    );
  }

  if (role === "manager") {
    return (
      <Routes>
        <Route path="/manager" element={<ManagerLayout />}>
          <Route index element={<ManagerDashboard />} />
          <Route path="claims" element={<ManagerClaims />} />
          <Route path="claims/:id" element={<ManagerClaimReview />} />
        </Route>
        {/* Redirect root and unknown paths to manager dashboard */}
        <Route path="*" element={<Navigate to="/manager" replace />} />
      </Routes>
    );
  }

  if (role === "finance") {
    return (
      <Routes>
        <Route path="/finance" element={<FinanceLayout />}>
          <Route index element={<FinanceDashboard />} />
          <Route path="verification" element={<FinanceVerificationQueue />} />
          <Route path="claims/:id" element={<FinanceClaimReview />} />
          <Route path="payments" element={<FinancePayments />} />
          <Route path="reports" element={<FinanceReports />} />
        </Route>
        {/* Redirect root and unknown paths to finance dashboard */}
        <Route path="*" element={<Navigate to="/finance" replace />} />
      </Routes>
    );
  }

  return null;
}

export default function App() {
  return (
    <RoleProvider>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </RoleProvider>
  );
}

