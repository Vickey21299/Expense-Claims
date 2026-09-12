// Centralized API service layer.
// All data fetching and mutation goes through these functions.
// Staff, Manager, and Finance flows are 100% connected to the live FastAPI backend.

import { CURRENT_USER, CURRENT_MANAGER, CURRENT_FINANCE } from "../data/users";

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000/api/v1";

// ---------------------------------------------------------------------------
// ---------------------------------------------------------------------------
// History & SLA Timeline Builder
// ---------------------------------------------------------------------------
function buildStructuredHistory(c, item = {}) {
  const rawHistory = item.status_history || c.status_history || [];
  const mgrComment = item.manager_review?.comment || c.manager_comment || c.reviewComment || null;
  const finComment = item.finance_review?.comment || c.finance_comment || c.financeVerification?.comment || null;

  let history = [];
  if (Array.isArray(rawHistory) && rawHistory.length > 0) {
    history = rawHistory.map((h) => {
      let comment = h.comment;
      let actor = h.actor_name;

      const evLower = (h.event_label || "").toLowerCase();
      const toStatus = h.to_status || "";

      // Enrich with manager comment if applicable
      if (
        !comment &&
        mgrComment &&
        (toStatus === "APPROVED" || toStatus === "MANAGER_CONFIRMED" || (toStatus === "REJECTED" && evLower.includes("manager")))
      ) {
        comment = mgrComment;
      }

      // Enrich with finance comment if applicable
      if (
        !comment &&
        finComment &&
        (toStatus === "READY_FOR_PAYMENT" || toStatus === "PAID" || (toStatus === "REJECTED" && evLower.includes("finance")))
      ) {
        comment = finComment;
      }

      return {
        id: h.id,
        event: h.event_label || `Status changed to ${toStatus}`,
        timestamp: h.occurred_at,
        done: true,
        comment,
        actor,
        fromStatus: h.from_status,
        toStatus: h.to_status,
      };
    });
  } else if (Array.isArray(c.history)) {
    history = [...c.history];
  }

  // Active status progression indicators
  if (c.status === "SUBMITTED") {
    history.push({
      event: "Awaiting Manager Review",
      timestamp: null,
      done: false,
      isCurrent: true,
      actor: c.manager?.name || "Rahul Sharma",
    });
  } else if (c.status === "UNDER_REVIEW") {
    history.push({
      event: "Manager Review In Progress",
      timestamp: null,
      done: false,
      isCurrent: true,
      actor: c.manager?.name || "Rahul Sharma",
    });
  } else if (c.status === "FLAGGED") {
    history.push({
      event: "Flagged — Awaiting Manager Business Context Justification",
      timestamp: null,
      done: false,
      isCurrent: true,
      actor: c.manager?.name || "Rahul Sharma",
    });
  } else if (c.status === "MANAGER_CONFIRMED" || c.status === "APPROVED") {
    history.push({
      event: "Awaiting Finance Audit & Clearance",
      timestamp: null,
      done: false,
      isCurrent: true,
      actor: "Anita Joshi",
    });
  } else if (c.status === "READY_FOR_PAYMENT") {
    history.push({
      event: "Queued for Reimbursement Disbursement",
      timestamp: null,
      done: false,
      isCurrent: true,
      actor: "Anita Joshi",
    });
  }

  return history;
}

// ---------------------------------------------------------------------------
// Normalizer for Staff claims from backend
// ---------------------------------------------------------------------------
function normalizeStaffClaim(c) {
  if (!c) return null;
  const receiptDoc = c.documents && c.documents.length > 0 ? c.documents[0] : null;
  const receiptUrl = receiptDoc ? receiptDoc.file_url : c.receipt_url || c.receiptUrl || null;

  const history = buildStructuredHistory(c);

  return {
    ...c,
    id: c.id,
    claimRef: c.claim_ref || c.id,
    claim_ref: c.claim_ref || c.id,
    merchant: c.merchant || "Draft Claim",
    amount: Number(c.amount) || 0,
    currency: c.currency || "INR",
    category: c.claim_type || c.category || "General",
    claim_type: c.claim_type || c.category || "General",
    date: c.claim_date || (c.created_at ? c.created_at.slice(0, 10) : ""),
    claim_date: c.claim_date || (c.created_at ? c.created_at.slice(0, 10) : ""),
    description: c.description || "",
    status: c.status || "DRAFT",
    ocrStatus: c.ocr_status,
    verificationStatus: c.verification_status,
    financeStatus: c.finance_status,
    paymentReference: c.payment_reference,
    manager: CURRENT_USER.manager,
    submittedAt: c.submitted_at,
    createdAt: c.created_at,
    updatedAt: c.updated_at,
    receiptUrl,
    documents: c.documents || (receiptDoc ? [receiptDoc] : []),
    history,
    verificationResults: c.verification_results || [],
    duplicateMatches: c.duplicate_matches || [],
    latestVerification: c.latest_verification || null,
  };
}

// ---------------------------------------------------------------------------
// Staff API functions (Real FastAPI backend integration)
// ---------------------------------------------------------------------------

/**
 * Get all claims for the current user (Vickey Kumar).
 * GET /api/v1/users/{email}/claims
 */
export async function getMyClaims() {
  try {
    const userIdent = CURRENT_USER.email || "vickey.kumar@company.com";
    const res = await fetch(`${API_BASE_URL}/users/${encodeURIComponent(userIdent)}/claims`);
    if (!res.ok) {
      const err = await res.text();
      throw new Error(`Failed to fetch claims: ${res.status} ${err}`);
    }
    const data = await res.json();
    const claimsList = (data.claims || []).map(normalizeStaffClaim);
    return claimsList.sort((a, b) => {
      const timeA = new Date(a.createdAt || a.created_at || a.submittedAt || a.submitted_at || a.date || 0).getTime();
      const timeB = new Date(b.createdAt || b.created_at || b.submittedAt || b.submitted_at || b.date || 0).getTime();
      return timeB - timeA;
    });
  } catch (error) {
    console.error("Error fetching my claims from backend:", error);
    throw error;
  }
}

/**
 * Get a single claim by UUID or claim_ref.
 * GET /api/v1/claims/{id}
 */
export async function getClaim(id) {
  try {
    const res = await fetch(`${API_BASE_URL}/claims/${id}`);
    if (!res.ok) {
      const err = await res.text();
      throw new Error(`Claim ${id} not found: ${err}`);
    }
    const data = await res.json();
    return normalizeStaffClaim(data);
  } catch (error) {
    console.error(`Error fetching claim ${id}:`, error);
    throw error;
  }
}

/**
 * Create a new claim (saves as DRAFT).
 * POST /api/v1/claims
 * @param {Object} data - claim fields: merchant, amount, currency, category, date, description
 * @returns {Object} The created claim with id and status DRAFT
 */
export async function createClaim(data) {
  try {
    const payload = {
      employee_id: CURRENT_USER.uuid || "4b987739-6880-4e65-a3c7-031bf7a59139",
      manager_id: CURRENT_USER.managerUuid || "28ac25ae-735f-4085-a6ed-c765be651ef1",
      merchant: data.merchant || "",
      claim_type: data.category || "Other",
      amount: Number(data.amount) || 0,
      currency: data.currency || "INR",
      claim_date: data.date || new Date().toISOString().slice(0, 10),
      description: data.description || "",
    };
    const res = await fetch(`${API_BASE_URL}/claims`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.text();
      throw new Error(`Failed to create claim: ${err}`);
    }
    const created = await res.json();
    return normalizeStaffClaim(created);
  } catch (error) {
    console.error("Error creating claim:", error);
    throw error;
  }
}

/**
 * Update an existing draft claim's fields.
 * PUT /api/v1/claims/{id}
 * @param {string} id
 * @param {Object} data - fields to update
 */
export async function updateClaim(id, data) {
  try {
    const payload = {};
    if (data.merchant !== undefined) payload.merchant = data.merchant;
    if (data.category !== undefined) payload.claim_type = data.category;
    if (data.amount !== undefined) payload.amount = Number(data.amount);
    if (data.currency !== undefined) payload.currency = data.currency;
    if (data.date !== undefined) payload.claim_date = data.date;
    if (data.description !== undefined) payload.description = data.description;

    const res = await fetch(`${API_BASE_URL}/claims/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.text();
      throw new Error(`Failed to update claim: ${err}`);
    }
    const updated = await res.json();
    return normalizeStaffClaim(updated);
  } catch (error) {
    console.error(`Error updating claim ${id}:`, error);
    throw error;
  }
}

/**
 * Submit a claim — transitions status from DRAFT to SUBMITTED and runs deterministic verification.
 * POST /api/v1/claims/{id}/submit
 * @param {string} id
 */
export async function submitClaim(id) {
  try {
    // Check if claim was already transitioned by auto-verification pipeline
    try {
      const claimBefore = await getClaim(id);
      if (claimBefore && claimBefore.status !== "DRAFT") {
        return claimBefore;
      }
    } catch {
      // Continue to submit if getClaim check didn't catch it
    }

    const res = await fetch(`${API_BASE_URL}/claims/${id}/submit`, {
      method: "POST",
    });
    if (!res.ok) {
      if (res.status === 409) {
        // Claim was already transitioned out of DRAFT
        return await getClaim(id);
      }
      const err = await res.text();
      throw new Error(`Failed to submit claim: ${err}`);
    }

    // Automatically trigger verification in the background if needed
    try {
      await fetch(`${API_BASE_URL}/verification/claims/${id}/run`, {
        method: "POST",
      });
    } catch (verErr) {
      console.warn("Verification pipeline trigger warning:", verErr);
    }

    return await getClaim(id);
  } catch (error) {
    console.error(`Error submitting claim ${id}:`, error);
    throw error;
  }
}

/**
 * Upload a receipt file to Supabase Storage via FastAPI.
 * POST /api/v1/claims/{claimId}/documents
 */
export async function uploadReceipt(claimId, file) {
  try {
    const formData = new FormData();
    formData.append("file", file);

    const res = await fetch(`${API_BASE_URL}/claims/${claimId}/documents?auto_verify=true`, {
      method: "POST",
      body: formData,
    });
    if (!res.ok) {
      const err = await res.text();
      throw new Error(`Failed to upload receipt: ${err}`);
    }
    const docData = await res.json();
    return {
      receiptUrl: docData.file_url || (docData.document && docData.document.storage_path) || null,
      ...docData,
    };
  } catch (error) {
    console.error(`Error uploading receipt for claim ${claimId}:`, error);
    throw error;
  }
}

/**
 * Extract data from a receipt image/pdf using Gemini Vision API.
 * POST /api/v1/documents/analyze
 * @param {File} file - receipt file object
 * @returns {Object} extracted fields: merchant, amount, date, category, description, line_items, warnings
 */
export async function analyzeReceipt(file) {
  try {
    const formData = new FormData();
    formData.append("file", file);

    const res = await fetch(`${API_BASE_URL}/documents/analyze`, {
      method: "POST",
      body: formData,
    });
    if (!res.ok) {
      const err = await res.text();
      throw new Error(`Failed to analyze receipt: ${err}`);
    }
    return await res.json();
  } catch (error) {
    console.error("Error analyzing receipt:", error);
    throw error;
  }
}

// ---------------------------------------------------------------------------
// Manager Normalizer
// ---------------------------------------------------------------------------
function normalizeManagerClaim(item) {
  if (!item) return null;
  // Item can be a raw claim row or a dossier { claim, employee, documents, extracted_data, ... }
  const c = item.claim ? item.claim : item;
  const emp = item.employee || c.employee || null;
  const docs = item.documents || (c.documents ? c.documents : []);
  const receiptDoc = docs && docs.length > 0 ? docs[0] : null;
  const receiptUrl = receiptDoc ? receiptDoc.file_url : c.receipt_url || c.receiptUrl || null;

  const history = buildStructuredHistory(c, item);

  const matchedCandidates = item.matched_candidates || c.matched_candidates || [];
  const llmData = item.llm_analysis || c.llm_analysis || null;
  const verData = item.verification || c.verification || null;

  const isFlagged = c.status === "FLAGGED" || c.verification_status === "FLAGGED" || (llmData && llmData.duplicate_risk_percentage >= 50);

  return {
    ...c,
    id: c.id,
    claimRef: c.claim_ref || c.id,
    claim_ref: c.claim_ref || c.id,
    merchant: c.merchant || "Expense Claim",
    amount: Number(c.amount) || 0,
    currency: c.currency || "INR",
    category: c.claim_type || c.category || "General",
    claim_type: c.claim_type || c.category || "General",
    date: c.claim_date || (c.created_at ? c.created_at.slice(0, 10) : ""),
    claim_date: c.claim_date || (c.created_at ? c.created_at.slice(0, 10) : ""),
    description: c.description || "",
    status: c.status || "SUBMITTED",
    ocrStatus: c.ocr_status,
    verificationStatus: c.verification_status,
    financeStatus: c.finance_status,
    paymentReference: c.payment_reference,
    submittedAt: c.submitted_at || c.created_at,
    createdAt: c.created_at,
    updatedAt: c.updated_at,
    employee: emp
      ? {
          id: emp.id,
          name: emp.full_name || emp.name || "Employee",
          email: emp.email || "",
          department: emp.department || "Engineering",
          role: emp.job_title || emp.role || "Staff",
        }
      : {
          id: c.employee_id,
          name: c.employee_name || "Employee",
          email: "",
          department: "Engineering",
          role: "Staff",
        },
    manager: CURRENT_MANAGER,
    receiptUrl,
    documents: docs,
    extracted_data: item.extracted_data || null,
    verification: verData,
    llm_analysis: llmData,
    matched_candidates: matchedCandidates,
    allowed_actions: item.allowed_actions || (isFlagged ? ["CONFIRM_CONTEXT", "REJECT"] : ["APPROVE", "REJECT"]),
    duplicate_risk_percentage: c.duplicate_risk_percentage || (llmData ? llmData.duplicate_risk_percentage : null),
    risk_classification: c.risk_classification || (llmData ? llmData.risk_classification : null),
    manager_recommendation: c.manager_recommendation || (llmData ? llmData.manager_recommendation : null),
    duplicate: isFlagged
      ? {
          flagged: true,
          matchedClaimId: matchedCandidates.length > 0 ? (matchedCandidates[0].claim_ref || matchedCandidates[0].claim_id) : (llmData ? llmData.matched_claim_ref : null),
          signals: matchedCandidates.length > 0 ? (matchedCandidates[0].match_reasons || ["Potential duplicate detected"]) : ["High similarity score detected"],
          assessment: llmData ? (llmData.reasoning || llmData.manager_recommendation) : (verData ? verData.explanation : "Potential duplicate detected by verification engine."),
        }
      : null,
    history,
  };
}

// ---------------------------------------------------------------------------
// Manager API functions (Live FastAPI backend)
// ---------------------------------------------------------------------------

/**
 * Get all claims for the manager's review queue.
 * GET /api/v1/manager/claims?manager_id={uuid}
 */
export async function getManagerClaims(managerId = CURRENT_MANAGER.uuid || "28ac25ae-735f-4085-a6ed-c765be651ef1") {
  try {
    const url = managerId
      ? `${API_BASE_URL}/manager/claims?manager_id=${managerId}`
      : `${API_BASE_URL}/manager/claims`;
    const res = await fetch(url);
    if (!res.ok) {
      const err = await res.text();
      throw new Error(`Failed to fetch manager claims: ${err}`);
    }
    const data = await res.json();
    const claims = (data.claims || []).map(normalizeManagerClaim);
    return claims.sort((a, b) => {
      const dateA = new Date(a.submittedAt || a.date || 0).getTime();
      const dateB = new Date(b.submittedAt || b.date || 0).getTime();
      return dateB - dateA;
    });
  } catch (error) {
    console.error("Error fetching manager claims from backend:", error);
    throw error;
  }
}

/**
 * Get a single manager claim review dossier by UUID or claim_ref.
 * GET /api/v1/manager/claims/{id}
 */
export async function getManagerClaim(id) {
  try {
    const res = await fetch(`${API_BASE_URL}/manager/claims/${id}`);
    if (!res.ok) {
      const err = await res.text();
      throw new Error(`Claim ${id} not found in manager review: ${err}`);
    }
    const dossier = await res.json();
    return normalizeManagerClaim(dossier);
  } catch (error) {
    console.error(`Error fetching manager claim ${id}:`, error);
    throw error;
  }
}

/**
 * Approve a clean claim — transitions status to READY_FOR_PAYMENT.
 * POST /api/v1/manager/claims/{id}/approve
 * @param {string} id
 * @param {string} comment - optional manager comment
 */
export async function approveClaim(id, comment = "") {
  try {
    const payload = {
      manager_id: CURRENT_MANAGER.uuid || "28ac25ae-735f-4085-a6ed-c765be651ef1",
      comment: comment || "Approved by manager",
    };
    const res = await fetch(`${API_BASE_URL}/manager/claims/${id}/approve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Approval failed" }));
      throw new Error(err.detail || "Approval failed");
    }
    return await getManagerClaim(id);
  } catch (error) {
    console.error(`Error approving claim ${id}:`, error);
    throw error;
  }
}

/**
 * Confirm business context for a FLAGGED claim — transitions status to MANAGER_CONFIRMED.
 * POST /api/v1/manager/claims/{id}/confirm
 * @param {string} id
 * @param {string} comment - required manager justification
 */
export async function confirmClaimContext(id, comment) {
  try {
    if (!comment || !comment.trim()) {
      throw new Error("Manager comment is required to confirm business context for a flagged claim.");
    }
    const payload = {
      manager_id: CURRENT_MANAGER.uuid || "28ac25ae-735f-4085-a6ed-c765be651ef1",
      comment: comment.trim(),
    };
    const res = await fetch(`${API_BASE_URL}/manager/claims/${id}/confirm`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Confirmation failed" }));
      throw new Error(err.detail || "Confirmation failed");
    }
    return await getManagerClaim(id);
  } catch (error) {
    console.error(`Error confirming claim ${id}:`, error);
    throw error;
  }
}

/**
 * Reject a claim — transitions status to REJECTED.
 * POST /api/v1/manager/claims/{id}/reject
 * @param {string} id
 * @param {string} reason - required rejection reason
 */
export async function rejectClaim(id, reason) {
  try {
    if (!reason || !reason.trim()) {
      throw new Error("Rejection reason is required");
    }
    const payload = {
      manager_id: CURRENT_MANAGER.uuid || "28ac25ae-735f-4085-a6ed-c765be651ef1",
      comment: reason.trim(),
    };
    const res = await fetch(`${API_BASE_URL}/manager/claims/${id}/reject`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Rejection failed" }));
      throw new Error(err.detail || "Rejection failed");
    }
    return await getManagerClaim(id);
  } catch (error) {
    console.error(`Error rejecting claim ${id}:`, error);
    throw error;
  }
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
// Finance Normalizer
// ---------------------------------------------------------------------------
function normalizeFinanceClaim(item) {
  if (!item) return null;
  const c = item.claim ? item.claim : item;
  const emp = item.employee || c.employee || null;
  const docs = item.documents || (c.documents ? c.documents : []);
  const receiptDoc = docs && docs.length > 0 ? docs[0] : null;
  const receiptUrl = receiptDoc ? receiptDoc.file_url : c.receipt_url || c.receiptUrl || null;

  const history = buildStructuredHistory(c, item);

  const matchedCandidates = item.matched_candidates || c.matched_candidates || [];
  const llmData = item.llm_analysis || c.llm_analysis || null;
  const verData = item.verification || c.verification || null;
  const mgrReview = item.manager_review || (c.manager_comment ? { comment: c.manager_comment } : null);

  const isFlagged = c.status === "FLAGGED" || c.finance_status === "FINANCE_EXCEPTION" || c.verification_status === "FLAGGED" || (llmData && llmData.duplicate_risk_percentage >= 50);

  return {
    ...c,
    id: c.id,
    claimRef: c.claim_ref || c.id,
    claim_ref: c.claim_ref || c.id,
    merchant: c.merchant || "Expense Claim",
    amount: Number(c.amount) || 0,
    currency: c.currency || "INR",
    category: c.claim_type || c.category || "General",
    claim_type: c.claim_type || c.category || "General",
    date: c.claim_date || (c.created_at ? c.created_at.slice(0, 10) : ""),
    claim_date: c.claim_date || (c.created_at ? c.created_at.slice(0, 10) : ""),
    description: c.description || "",
    status: c.status || "APPROVED",
    ocrStatus: c.ocr_status,
    verificationStatus: c.verification_status,
    financeStatus: c.finance_status || (c.status === "READY_FOR_PAYMENT" ? "FINANCE_CLEARED" : (c.status === "REJECTED" ? "FINANCE_REJECTED" : (c.status === "PAID" ? "PAID" : "FINANCE_PENDING"))),
    finance_status: c.finance_status,
    paymentReference: c.payment_reference,
    payment_reference: c.payment_reference,
    submittedAt: c.submitted_at || c.created_at,
    createdAt: c.created_at,
    updatedAt: c.updated_at,
    employee: emp
      ? {
          id: emp.id,
          name: emp.full_name || emp.name || "Employee",
          email: emp.email || "",
          department: emp.department || "Engineering",
          role: emp.job_title || emp.role || "Staff",
        }
      : {
          id: c.employee_id,
          name: c.employee_name || "Employee",
          email: "",
          department: "Engineering",
          role: "Staff",
        },
    manager: {
      name: "Rahul Sharma",
      id: c.manager_id,
    },
    reviewComment: mgrReview?.comment || c.manager_comment || null,
    manager_review: mgrReview,
    receiptUrl,
    documents: docs,
    extracted_data: item.extracted_data || null,
    verification: verData,
    llm_analysis: llmData,
    matched_candidates: matchedCandidates,
    payment_info: item.payment_info || null,
    allowed_actions: item.allowed_actions || (c.status === "READY_FOR_PAYMENT" ? ["EXECUTE_PAYMENT", "REJECT"] : ["CLEAR_ANOMALY", "REJECT"]),
    duplicate_risk_percentage: c.duplicate_risk_percentage || (llmData ? llmData.duplicate_risk_percentage : null),
    risk_classification: c.risk_classification || (llmData ? llmData.risk_classification : null),
    manager_recommendation: c.manager_recommendation || (llmData ? llmData.manager_recommendation : null),
    duplicate: isFlagged
      ? {
          flagged: true,
          matchedClaimId: matchedCandidates.length > 0 ? (matchedCandidates[0].claim_ref || matchedCandidates[0].claim_id) : (llmData ? llmData.matched_claim_ref : null),
          signals: matchedCandidates.length > 0 ? (matchedCandidates[0].match_reasons || ["Potential duplicate detected"]) : ["Anomaly flag detected"],
          assessment: llmData ? (llmData.reasoning || llmData.manager_recommendation) : (verData ? verData.explanation : "Flagged for manual finance verification."),
        }
      : null,
    history,
  };
}

// ---------------------------------------------------------------------------
// Finance API functions (Live FastAPI backend)
// ---------------------------------------------------------------------------

/**
 * Get aggregate dashboard metrics for the Finance role.
 * GET /api/v1/finance/claims + live aggregations
 */
export async function getFinanceDashboard() {
  try {
    const claims = await getFinanceClaims({ financeStatus: "ALL" });
    const thisMonth = new Date().toISOString().slice(0, 7); // "YYYY-MM"

    const pending = claims.filter(
      (c) => c.financeStatus === "FINANCE_PENDING" || ["APPROVED", "MANAGER_CONFIRMED"].includes(c.status)
    ).length;

    const flagged = claims.filter(
      (c) => c.financeStatus === "FINANCE_EXCEPTION" || c.status === "FLAGGED"
    ).length;

    const readyForPayment = claims.filter((c) => c.status === "READY_FOR_PAYMENT").length;

    const paidClaims = claims.filter((c) => c.status === "PAID");
    const paidThisMonth = paidClaims.filter((c) => (c.submittedAt || c.date || "").startsWith(thisMonth)).length;

    const monthlySpend = paidClaims
      .filter((c) => (c.submittedAt || c.date || "").startsWith(thisMonth))
      .reduce((sum, c) => sum + (c.amount || 0), 0);

    const totalPaid = paidClaims.reduce((sum, c) => sum + (c.amount || 0), 0);

    return { pending, flagged, readyForPayment, paidThisMonth, monthlySpend, totalPaid };
  } catch (error) {
    console.error("Error fetching finance dashboard metrics:", error);
    throw error;
  }
}

/**
 * Get all claims visible to Finance, optionally filtered.
 * GET /api/v1/finance/claims
 * @param {Object} filters - { financeStatus, employee, category, search }
 */
export async function getFinanceClaims(filters = {}) {
  try {
    let url = `${API_BASE_URL}/finance/claims`;
    if (filters.financeStatus && filters.financeStatus !== "ALL") {
      url += `?finance_status=${encodeURIComponent(filters.financeStatus)}`;
    }

    const res = await fetch(url);
    if (!res.ok) {
      const err = await res.text();
      throw new Error(`Failed to fetch finance claims: ${err}`);
    }

    const data = await res.json();
    let results = (data.claims || []).map(normalizeFinanceClaim);

    // Client-side search and filters if specified
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
          c.claimRef?.toLowerCase().includes(q) ||
          c.merchant?.toLowerCase().includes(q) ||
          c.employee?.name?.toLowerCase().includes(q) ||
          c.description?.toLowerCase().includes(q)
      );
    }

    return results.sort((a, b) => {
      const dateA = new Date(a.submittedAt || a.date || 0).getTime();
      const dateB = new Date(b.submittedAt || b.date || 0).getTime();
      return dateB - dateA;
    });
  } catch (error) {
    console.error("Error fetching finance claims from backend:", error);
    throw error;
  }
}

/**
 * Get a single claim for Finance review.
 * GET /api/v1/finance/claims/{id}
 */
export async function getFinanceClaim(id) {
  try {
    const res = await fetch(`${API_BASE_URL}/finance/claims/${id}`);
    if (!res.ok) {
      const err = await res.text();
      throw new Error(`Claim ${id} not found in finance review: ${err}`);
    }
    const dossier = await res.json();
    return normalizeFinanceClaim(dossier);
  } catch (error) {
    console.error(`Error fetching finance claim ${id}:`, error);
    throw error;
  }
}

/**
 * Verify and clear a claim for payment.
 * POST /api/v1/finance/claims/{id}/clear
 * @param {string} id
 * @param {string} comment - optional explanation for clearing
 */
export async function verifyClaim(id, comment = "Verified and cleared for reimbursement payment") {
  try {
    const payload = {
      finance_user_id: CURRENT_FINANCE.uuid || "1dcd270f-f17b-40f9-a325-48979e93cd96",
      comment: comment || "Verified by finance",
    };
    const res = await fetch(`${API_BASE_URL}/finance/claims/${id}/clear`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Verification failed" }));
      throw new Error(err.detail || "Verification failed");
    }
    return await getFinanceClaim(id);
  } catch (error) {
    console.error(`Error verifying claim ${id}:`, error);
    throw error;
  }
}

/**
 * Clear a finance exception (e.g., duplicate reviewed and cleared).
 * POST /api/v1/finance/claims/{id}/clear
 * @param {string} id
 * @param {string} comment - required explanation for clearing
 */
export async function clearFinancialException(id, comment) {
  try {
    if (!comment || !comment.trim()) {
      throw new Error("Reason for clearing exception is required");
    }
    return await verifyClaim(id, comment);
  } catch (error) {
    console.error(`Error clearing exception for claim ${id}:`, error);
    throw error;
  }
}

/**
 * Confirm a duplicate and finance-reject the claim.
 * POST /api/v1/finance/claims/{id}/reject
 * @param {string} id
 * @param {string} reason - required rejection reason
 */
export async function confirmDuplicate(id, reason) {
  try {
    if (!reason || !reason.trim()) {
      throw new Error("Reason is required to confirm duplicate");
    }
    return await financeRejectClaim(id, reason);
  } catch (error) {
    console.error(`Error confirming duplicate for claim ${id}:`, error);
    throw error;
  }
}

/**
 * Finance reject a claim.
 * POST /api/v1/finance/claims/{id}/reject
 * @param {string} id
 * @param {string} reason - required rejection reason
 */
export async function financeRejectClaim(id, reason) {
  try {
    if (!reason || !reason.trim()) {
      throw new Error("Rejection reason is required");
    }
    const payload = {
      finance_user_id: CURRENT_FINANCE.uuid || "1dcd270f-f17b-40f9-a325-48979e93cd96",
      reason: reason.trim(),
    };
    const res = await fetch(`${API_BASE_URL}/finance/claims/${id}/reject`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Finance rejection failed" }));
      throw new Error(err.detail || "Finance rejection failed");
    }
    return await getFinanceClaim(id);
  } catch (error) {
    console.error(`Error rejecting claim ${id}:`, error);
    throw error;
  }
}

/**
 * Process payment for a READY_FOR_PAYMENT claim via PaymentService.
 * POST /api/v1/finance/claims/{id}/pay
 * @param {string} id
 * @param {string} [paymentReference]
 * @param {string} [notes]
 */
export async function payClaim(id, paymentReference = null, notes = "Processed via Finance disbursement") {
  try {
    const payload = {
      finance_user_id: CURRENT_FINANCE.uuid || "1dcd270f-f17b-40f9-a325-48979e93cd96",
      payment_reference: paymentReference,
      notes: notes,
    };
    const res = await fetch(`${API_BASE_URL}/finance/claims/${id}/pay`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Payment processing failed" }));
      throw new Error(err.detail || "Payment processing failed");
    }
    const payment = await res.json();
    return await getFinanceClaim(id).catch(() => ({ id, status: "PAID", paymentReference: payment.payment_reference }));
  } catch (error) {
    console.error(`Error processing payment for claim ${id}:`, error);
    throw error;
  }
}

/**
 * Get aggregated report data for the Finance Reports page from live claims.
 * @param {Object} filters - { period } ('this_month' | 'last_month' | 'all')
 */
export async function getFinanceReports(filters = {}) {
  try {
    const claims = await getFinanceClaims({ financeStatus: "ALL" });
    const now = new Date();
    const thisMonth = now.toISOString().slice(0, 7);
    const lastMonth = new Date(now.getFullYear(), now.getMonth() - 1, 1).toISOString().slice(0, 7);

    let scope = claims;
    if (filters.period === "this_month") {
      scope = claims.filter((c) => (c.submittedAt || c.date || "").startsWith(thisMonth));
    } else if (filters.period === "last_month") {
      scope = claims.filter((c) => (c.submittedAt || c.date || "").startsWith(lastMonth));
    }

    // Category breakdown
    const categoryMap = {};
    scope.forEach((c) => {
      const cat = c.category || "Other";
      if (!categoryMap[cat]) categoryMap[cat] = { count: 0, total: 0 };
      categoryMap[cat].count += 1;
      categoryMap[cat].total += c.amount || 0;
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
      if (c.financeStatus === "FINANCE_PENDING" || c.status === "APPROVED" || c.status === "MANAGER_CONFIRMED") employeeMap[name].pending += c.amount || 0;
    });
    const employeeSpend = Object.entries(employeeMap)
      .map(([name, data]) => ({ name, ...data }))
      .sort((a, b) => b.total - a.total);

    const totalSpend = scope.reduce((s, c) => s + (c.amount || 0), 0);
    const paidAmount = scope.filter((c) => c.status === "PAID").reduce((s, c) => s + (c.amount || 0), 0);
    const pendingAmount = scope.filter((c) => c.financeStatus === "FINANCE_PENDING" || ["APPROVED", "MANAGER_CONFIRMED"].includes(c.status)).reduce((s, c) => s + (c.amount || 0), 0);
    const flaggedAmount = scope.filter((c) => c.financeStatus === "FINANCE_EXCEPTION" || c.status === "FLAGGED").reduce((s, c) => s + (c.amount || 0), 0);

    return {
      totalClaims: scope.length,
      totalSpend,
      paidAmount,
      pendingAmount,
      flaggedAmount,
      categoryBreakdown,
      employeeSpend,
    };
  } catch (error) {
    console.error("Error generating finance reports:", error);
    throw error;
  }
}

