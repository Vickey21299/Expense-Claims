// Centralized API service layer.
// All data fetching and mutation goes through these functions.
// Currently backed by in-memory mock data.
// Replace the implementations here when FastAPI backend is ready.
// DO NOT call fetch/supabase directly from React components.

import { mockClaims, CURRENT_USER, managerClaims, CURRENT_MANAGER, CURRENT_FINANCE } from "../data/mockClaims";

// ---------------------------------------------------------------------------
// In-memory stores — persist across navigation within a session
// ---------------------------------------------------------------------------
let _claims = [...mockClaims];
let _managerClaims = [...managerClaims];
let _nextId = 1100;

// Simulate network latency for a realistic UX
const delay = (ms = 300) => new Promise((resolve) => setTimeout(resolve, ms));

// ---------------------------------------------------------------------------
// Staff API functions
// ---------------------------------------------------------------------------

/**
 * Get all claims for the current user.
 * TODO: Replace with GET /api/claims?user_id=current
 */
export async function getMyClaims() {
  await delay();
  return [..._claims].sort((a, b) => {
    const dateA = a.submittedAt || a.date || "";
    const dateB = b.submittedAt || b.date || "";
    return dateB.localeCompare(dateA);
  });
}

/**
 * Get a single claim by ID.
 * TODO: Replace with GET /api/claims/:id
 */
export async function getClaim(id) {
  await delay();
  const claim = _claims.find((c) => c.id === id);
  if (!claim) throw new Error(`Claim ${id} not found`);
  return { ...claim };
}

/**
 * Create a new claim (saves as DRAFT).
 * TODO: Replace with POST /api/claims
 * @param {Object} data - claim fields: merchant, amount, currency, category, date, description
 * @returns {Object} The created claim with id and status DRAFT
 */
export async function createClaim(data) {
  await delay(500);
  const now = new Date().toISOString();
  const newClaim = {
    id: `CLM-${_nextId++}`,
    merchant: data.merchant || "",
    amount: Number(data.amount) || 0,
    currency: data.currency || "INR",
    category: data.category || "",
    date: data.date || "",
    description: data.description || "",
    status: "DRAFT",
    manager: CURRENT_USER.manager,
    submittedAt: null,
    receiptUrl: data.receiptUrl || null,
    history: [
      { event: "Claim created as draft", timestamp: now, done: true },
    ],
  };
  _claims = [newClaim, ..._claims];
  return { ...newClaim };
}

/**
 * Update an existing draft claim's fields.
 * TODO: Replace with PATCH /api/claims/:id
 * @param {string} id
 * @param {Object} data - fields to update
 */
export async function updateClaim(id, data) {
  await delay(300);
  _claims = _claims.map((c) => {
    if (c.id !== id) return c;
    if (c.status !== "DRAFT") throw new Error("Only DRAFT claims can be edited");
    return { ...c, ...data };
  });
  return getClaim(id);
}

/**
 * Submit a claim — transitions status from DRAFT to SUBMITTED.
 * TODO: Replace with POST /api/claims/:id/submit
 * @param {string} id
 */
export async function submitClaim(id) {
  await delay(600);
  const now = new Date().toISOString();
  _claims = _claims.map((c) => {
    if (c.id !== id) return c;
    return {
      ...c,
      status: "SUBMITTED",
      submittedAt: now,
      history: [
        ...(c.history || []),
        { event: "Receipt information extracted", timestamp: now, done: true },
        { event: "Claim submitted", timestamp: now, done: true },
        { event: "Waiting for manager review", timestamp: null, done: false, isCurrent: true },
      ],
    };
  });
  return getClaim(id);
}

/**
 * Upload a receipt file (stub — returns a mock URL).
 * TODO: Replace with POST /api/claims/:id/receipt (multipart)
 */
export async function uploadReceipt(id, _file) {
  await delay(800);
  const mockUrl = `https://example.com/receipts/${id}.pdf`;
  _claims = _claims.map((c) =>
    c.id === id ? { ...c, receiptUrl: mockUrl } : c
  );
  return { receiptUrl: mockUrl };
}

/**
 * Mock AI extraction from a receipt image/text.
 * TODO: Replace with POST /api/receipts/analyze (sends file/text, returns extracted fields)
 * @param {string|File} receiptData - text paste or file object
 * @returns {Object} extracted fields
 */
export async function analyzeReceipt(_receiptData) {
  // Simulate AI processing time
  await delay(1800);

  // Mock AI-extracted data — in production this comes from the LLM pipeline
  const mockExtractions = [
    {
      merchant: "Amazon",
      amount: 2450,
      date: new Date().toISOString().split("T")[0],
      category: "Office Supplies",
      description: "Keyboard and mouse for office use",
    },
    {
      merchant: "Uber",
      amount: 840,
      date: new Date().toISOString().split("T")[0],
      category: "Travel",
      description: "Cab to client office",
    },
    {
      merchant: "Swiggy",
      amount: 680,
      date: new Date().toISOString().split("T")[0],
      category: "Meals",
      description: "Team lunch order",
    },
    {
      merchant: "MakeMyTrip",
      amount: 5200,
      date: new Date().toISOString().split("T")[0],
      category: "Travel",
      description: "Train ticket — project site visit",
    },
  ];

  return mockExtractions[Math.floor(Math.random() * mockExtractions.length)];
}

// ---------------------------------------------------------------------------
// Manager API functions
// ---------------------------------------------------------------------------

/**
 * Get all claims for the manager's team.
 * TODO: Replace with GET /api/manager/claims
 */
export async function getManagerClaims() {
  await delay();
  return [..._managerClaims].sort((a, b) => {
    const dateA = a.submittedAt || a.date || "";
    const dateB = b.submittedAt || b.date || "";
    return dateB.localeCompare(dateA);
  });
}

/**
 * Get a single manager claim by ID.
 * TODO: Replace with GET /api/manager/claims/:id
 */
export async function getManagerClaim(id) {
  await delay();
  const claim = _managerClaims.find((c) => c.id === id);
  if (!claim) throw new Error(`Claim ${id} not found`);
  return { ...claim };
}

/**
 * Approve a claim — transitions status to APPROVED.
 * Flagged claims remain flagged (duplicate.flagged stays true).
 * TODO: Replace with POST /api/manager/claims/:id/approve
 * @param {string} id
 * @param {string} comment - optional manager comment
 */
export async function approveClaim(id, comment = "") {
  await delay(600);
  const now = new Date().toISOString();
  _managerClaims = _managerClaims.map((c) => {
    if (c.id !== id) return c;
    // Remove any isCurrent from existing history
    const updatedHistory = (c.history || []).map((h) => ({ ...h, isCurrent: false, done: true }));
    return {
      ...c,
      status: "APPROVED",
      reviewComment: comment || null,
      history: [
        ...updatedHistory,
        {
          event: `Manager approved — ${CURRENT_MANAGER.name}`,
          timestamp: now,
          done: true,
          comment: comment || null,
        },
        {
          event: "Forwarded to Finance",
          timestamp: null,
          done: false,
          isCurrent: true,
        },
      ],
    };
  });
  return getManagerClaim(id);
}

/**
 * Reject a claim — transitions status to REJECTED.
 * TODO: Replace with POST /api/manager/claims/:id/reject
 * @param {string} id
 * @param {string} reason - required rejection reason
 */
export async function rejectClaim(id, reason) {
  await delay(600);
  if (!reason || !reason.trim()) throw new Error("Rejection reason is required");
  const now = new Date().toISOString();
  _managerClaims = _managerClaims.map((c) => {
    if (c.id !== id) return c;
    // Remove any isCurrent from existing history
    const updatedHistory = (c.history || []).map((h) => ({ ...h, isCurrent: false, done: true }));
    return {
      ...c,
      status: "REJECTED",
      reviewComment: reason,
      history: [
        ...updatedHistory,
        {
          event: `Manager rejected — ${CURRENT_MANAGER.name}`,
          timestamp: now,
          done: true,
          comment: reason,
        },
      ],
    };
  });
  return getManagerClaim(id);
}

// ---------------------------------------------------------------------------
// Utility: category list (will come from /api/categories later)
// ---------------------------------------------------------------------------
export const EXPENSE_CATEGORIES = [
  "Travel",
  "Accommodation",
  "Meals",
  "Office Supplies",
  "Software & Subscriptions",
  "Training & Conferences",
  "Marketing",
  "Other",
];

// ---------------------------------------------------------------------------
// Finance API functions
// ---------------------------------------------------------------------------

// Finance uses managerClaims as its source (all team claims flow to finance).
// The store is shared with manager to keep mutations visible across both views.
let _financeClaims = _managerClaims; // reference — mutations on _managerClaims are visible

function _getFinanceClaims() {
  // Re-sync from _managerClaims so any manager mutations (approve/reject) are reflected.
  return _managerClaims;
}

/**
 * Get aggregate dashboard metrics for the Finance role.
 * TODO: Replace with GET /api/finance/dashboard
 */
export async function getFinanceDashboard() {
  await delay();
  const claims = _getFinanceClaims();
  const thisMonth = new Date().toISOString().slice(0, 7); // "YYYY-MM"

  const pending = claims.filter((c) => c.financeStatus === "FINANCE_PENDING").length;
  const flagged = claims.filter((c) => c.financeStatus === "FINANCE_EXCEPTION").length;
  const readyForPayment = claims.filter((c) => c.status === "READY_FOR_PAYMENT").length;
  const paidThisMonth = claims.filter(
    (c) => c.status === "PAID" && (c.submittedAt || "").startsWith(thisMonth)
  ).length;
  const monthlySpend = claims
    .filter((c) => c.status === "PAID" && (c.submittedAt || "").startsWith(thisMonth))
    .reduce((sum, c) => sum + (c.amount || 0), 0);
  const totalPaid = claims
    .filter((c) => c.status === "PAID")
    .reduce((sum, c) => sum + (c.amount || 0), 0);

  return { pending, flagged, readyForPayment, paidThisMonth, monthlySpend, totalPaid };
}

/**
 * Get all claims visible to Finance, optionally filtered.
 * TODO: Replace with GET /api/finance/claims
 * @param {Object} filters - { status, financeStatus, employee, category, search }
 */
export async function getFinanceClaims(filters = {}) {
  await delay();
  let results = [..._getFinanceClaims()];

  // Only show claims that are in manager-reviewed or later stages
  results = results.filter((c) =>
    ["APPROVED", "READY_FOR_PAYMENT", "PAID", "REJECTED", "FLAGGED"].includes(c.status) ||
    c.financeStatus !== null
  );

  if (filters.financeStatus && filters.financeStatus !== "ALL") {
    if (filters.financeStatus === "FINANCE_PENDING") {
      results = results.filter((c) => c.financeStatus === "FINANCE_PENDING");
    } else if (filters.financeStatus === "FINANCE_EXCEPTION") {
      results = results.filter((c) => c.financeStatus === "FINANCE_EXCEPTION");
    } else if (filters.financeStatus === "FINANCE_CLEARED") {
      results = results.filter((c) => c.financeStatus === "FINANCE_CLEARED");
    } else if (filters.financeStatus === "FINANCE_REJECTED") {
      results = results.filter((c) => c.financeStatus === "FINANCE_REJECTED");
    } else if (filters.financeStatus === "PAID") {
      results = results.filter((c) => c.status === "PAID");
    }
  }

  if (filters.employee) {
    const q = filters.employee.toLowerCase();
    results = results.filter((c) => c.employee?.name?.toLowerCase().includes(q));
  }

  if (filters.category) {
    results = results.filter((c) => c.category === filters.category);
  }

  if (filters.search) {
    const q = filters.search.toLowerCase();
    results = results.filter(
      (c) =>
        c.id?.toLowerCase().includes(q) ||
        c.merchant?.toLowerCase().includes(q) ||
        c.employee?.name?.toLowerCase().includes(q) ||
        c.description?.toLowerCase().includes(q)
    );
  }

  return results.sort((a, b) => {
    const dateA = a.submittedAt || a.date || "";
    const dateB = b.submittedAt || b.date || "";
    return dateB.localeCompare(dateA);
  });
}

/**
 * Get a single claim for Finance review.
 * TODO: Replace with GET /api/finance/claims/:id
 */
export async function getFinanceClaim(id) {
  await delay();
  const claim = _getFinanceClaims().find((c) => c.id === id);
  if (!claim) throw new Error(`Claim ${id} not found`);
  return { ...claim };
}

/**
 * Verify and clear a claim for payment.
 * Sets financeStatus → FINANCE_CLEARED, status → READY_FOR_PAYMENT.
 * TODO: Replace with POST /api/finance/claims/:id/verify
 * @param {string} id
 * @param {string} comment - required verification comment
 */
export async function verifyClaim(id, comment) {
  await delay(600);
  if (!comment || !comment.trim()) throw new Error("Verification comment is required");
  const now = new Date().toISOString();
  _managerClaims = _managerClaims.map((c) => {
    if (c.id !== id) return c;
    if (c.status === "PAID") throw new Error("PAID claims cannot be modified");
    const updatedHistory = (c.history || []).map((h) => ({ ...h, isCurrent: false, done: true }));
    return {
      ...c,
      status: "READY_FOR_PAYMENT",
      financeStatus: "FINANCE_CLEARED",
      financeVerification: { cleared: true, comment: comment.trim() },
      history: [
        ...updatedHistory,
        {
          event: `Finance verified — ${CURRENT_FINANCE.name}`,
          timestamp: now,
          done: true,
          comment: comment.trim(),
        },
        { event: "Ready for payment", timestamp: null, done: false, isCurrent: true },
      ],
    };
  });
  return getFinanceClaim(id);
}

/**
 * Clear a finance exception (e.g., duplicate reviewed and cleared).
 * Sets financeStatus → FINANCE_CLEARED, status → READY_FOR_PAYMENT.
 * TODO: Replace with POST /api/finance/claims/:id/clear-exception
 * @param {string} id
 * @param {string} comment - required explanation for clearing
 */
export async function clearFinancialException(id, comment) {
  await delay(600);
  if (!comment || !comment.trim()) throw new Error("Reason for clearing exception is required");
  const now = new Date().toISOString();
  _managerClaims = _managerClaims.map((c) => {
    if (c.id !== id) return c;
    if (c.status === "PAID") throw new Error("PAID claims cannot be modified");
    const updatedHistory = (c.history || []).map((h) => ({ ...h, isCurrent: false, done: true }));
    return {
      ...c,
      status: "READY_FOR_PAYMENT",
      financeStatus: "FINANCE_CLEARED",
      financeVerification: { cleared: true, comment: comment.trim() },
      history: [
        ...updatedHistory,
        {
          event: `Finance exception cleared — ${CURRENT_FINANCE.name}`,
          timestamp: now,
          done: true,
          comment: comment.trim(),
        },
        { event: "Ready for payment", timestamp: null, done: false, isCurrent: true },
      ],
    };
  });
  return getFinanceClaim(id);
}

/**
 * Confirm a duplicate and finance-reject the claim.
 * Sets financeStatus → FINANCE_REJECTED.
 * TODO: Replace with POST /api/finance/claims/:id/confirm-duplicate
 * @param {string} id
 * @param {string} reason - required rejection reason
 */
export async function confirmDuplicate(id, reason) {
  await delay(600);
  if (!reason || !reason.trim()) throw new Error("Reason is required to confirm duplicate");
  const now = new Date().toISOString();
  _managerClaims = _managerClaims.map((c) => {
    if (c.id !== id) return c;
    if (c.status === "PAID") throw new Error("PAID claims cannot be modified");
    const updatedHistory = (c.history || []).map((h) => ({ ...h, isCurrent: false, done: true }));
    return {
      ...c,
      financeStatus: "FINANCE_REJECTED",
      financeVerification: { cleared: false, comment: reason.trim() },
      history: [
        ...updatedHistory,
        {
          event: `Duplicate confirmed — Finance rejected — ${CURRENT_FINANCE.name}`,
          timestamp: now,
          done: true,
          comment: reason.trim(),
        },
      ],
    };
  });
  return getFinanceClaim(id);
}

/**
 * Finance reject a claim (non-duplicate reason).
 * Sets financeStatus → FINANCE_REJECTED.
 * TODO: Replace with POST /api/finance/claims/:id/reject
 * @param {string} id
 * @param {string} reason - required rejection reason
 */
export async function financeRejectClaim(id, reason) {
  await delay(600);
  if (!reason || !reason.trim()) throw new Error("Rejection reason is required");
  const now = new Date().toISOString();
  _managerClaims = _managerClaims.map((c) => {
    if (c.id !== id) return c;
    if (c.status === "PAID") throw new Error("PAID claims cannot be modified");
    const updatedHistory = (c.history || []).map((h) => ({ ...h, isCurrent: false, done: true }));
    return {
      ...c,
      financeStatus: "FINANCE_REJECTED",
      financeVerification: { cleared: false, comment: reason.trim() },
      history: [
        ...updatedHistory,
        {
          event: `Finance rejected — ${CURRENT_FINANCE.name}`,
          timestamp: now,
          done: true,
          comment: reason.trim(),
        },
      ],
    };
  });
  return getFinanceClaim(id);
}

/**
 * Process payment for a READY_FOR_PAYMENT claim.
 * Generates a mock payment reference, sets status → PAID.
 * Cannot pay flagged/exception claims.
 * TODO: Replace with POST /api/finance/claims/:id/pay
 * @param {string} id
 */
export async function payClaim(id) {
  await delay(800);
  const now = new Date().toISOString();
  const dateStr = now.slice(0, 10);
  const refNum = Math.floor(Math.random() * 90000) + 10000;
  const paymentReference = `PAY-${dateStr}-${refNum}`;

  _managerClaims = _managerClaims.map((c) => {
    if (c.id !== id) return c;
    if (c.status === "PAID") throw new Error("Claim already paid");
    if (c.status !== "READY_FOR_PAYMENT") throw new Error("Claim must be READY_FOR_PAYMENT to process payment");
    if (c.financeStatus !== "FINANCE_CLEARED") throw new Error("Finance must clear the claim before payment");
    const updatedHistory = (c.history || []).map((h) => ({ ...h, isCurrent: false, done: true }));
    return {
      ...c,
      status: "PAID",
      paymentReference,
      history: [
        ...updatedHistory,
        {
          event: `Payment processed — ${CURRENT_FINANCE.name}`,
          timestamp: now,
          done: true,
          comment: `Payment reference: ${paymentReference}`,
        },
      ],
    };
  });
  return getFinanceClaim(id);
}

/**
 * Get aggregated report data for the Finance Reports page.
 * TODO: Replace with GET /api/finance/reports
 * @param {Object} filters - { period } ('this_month' | 'last_month' | 'all')
 */
export async function getFinanceReports(filters = {}) {
  await delay(400);
  const claims = _getFinanceClaims();
  const now = new Date();
  const thisMonth = now.toISOString().slice(0, 7);
  const lastMonth = new Date(now.getFullYear(), now.getMonth() - 1, 1).toISOString().slice(0, 7);

  let scope = claims;
  if (filters.period === "this_month") {
    scope = claims.filter((c) => (c.submittedAt || "").startsWith(thisMonth));
  } else if (filters.period === "last_month") {
    scope = claims.filter((c) => (c.submittedAt || "").startsWith(lastMonth));
  }

  // Category breakdown
  const categoryMap = {};
  scope.forEach((c) => {
    if (!categoryMap[c.category]) categoryMap[c.category] = { count: 0, total: 0 };
    categoryMap[c.category].count += 1;
    categoryMap[c.category].total += c.amount || 0;
  });
  const categoryBreakdown = Object.entries(categoryMap)
    .map(([category, data]) => ({ category, ...data }))
    .sort((a, b) => b.total - a.total);

  // Employee spend
  const employeeMap = {};
  scope.forEach((c) => {
    const name = c.employee?.name || "Unknown";
    if (!employeeMap[name]) employeeMap[name] = { count: 0, total: 0, approved: 0, pending: 0 };
    employeeMap[name].count += 1;
    employeeMap[name].total += c.amount || 0;
    if (c.status === "PAID" || c.status === "READY_FOR_PAYMENT") employeeMap[name].approved += c.amount || 0;
    if (c.financeStatus === "FINANCE_PENDING") employeeMap[name].pending += c.amount || 0;
  });
  const employeeSpend = Object.entries(employeeMap)
    .map(([name, data]) => ({ name, ...data }))
    .sort((a, b) => b.total - a.total);

  const totalSpend = scope.reduce((s, c) => s + (c.amount || 0), 0);
  const paidAmount = scope.filter((c) => c.status === "PAID").reduce((s, c) => s + (c.amount || 0), 0);
  const pendingAmount = scope.filter((c) => c.financeStatus === "FINANCE_PENDING").reduce((s, c) => s + (c.amount || 0), 0);
  const flaggedAmount = scope.filter((c) => c.financeStatus === "FINANCE_EXCEPTION").reduce((s, c) => s + (c.amount || 0), 0);

  return {
    totalClaims: scope.length,
    totalSpend,
    paidAmount,
    pendingAmount,
    flaggedAmount,
    categoryBreakdown,
    employeeSpend,
  };
}

