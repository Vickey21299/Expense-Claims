// CreateClaim — receipt-first expense submission flow.
// Step 1: Upload receipt or paste text → mock AI extraction
// Step 2: Review & edit extracted fields → Save Draft or Submit

import { useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { Upload, FileText, Check, Loader2, ArrowLeft, User, AlertCircle, HelpCircle } from "lucide-react";
import { analyzeReceipt, createClaim, submitClaim, EXPENSE_CATEGORIES } from "../../services/api";
import { CURRENT_USER } from "../../data/mockClaims";

const STEPS = { UPLOAD: "upload", ANALYZING: "analyzing", REVIEW: "review", SUBMITTING: "submitting", SUCCESS: "success" };

const EMPTY_FORM = {
  merchant: "",
  amount: "",
  date: "",
  category: "",
  description: "",
};

const REQUIRED_FIELDS = ["merchant", "amount", "date", "category"];

export default function CreateClaim() {
  const navigate = useNavigate();
  const fileInputRef = useRef(null);
  const [step, setStep] = useState(STEPS.UPLOAD);
  const [pasteText, setPasteText] = useState("");
  const [form, setForm] = useState(EMPTY_FORM);
  const [errors, setErrors] = useState({});
  const [dragOver, setDragOver] = useState(false);
  const [uploadedFileName, setUploadedFileName] = useState(null);
  const [selectedFile, setSelectedFile] = useState(null);

  // ── Handlers ──────────────────────────────────────────────

  function handleFileSelect(file) {
    if (!file) return;
    setUploadedFileName(file.name);
    setSelectedFile(file);
  }

  async function handleAnalyzeBill() {
    if (!selectedFile) return;
    setStep(STEPS.ANALYZING);
    try {
      const extracted = await analyzeReceipt(selectedFile);
      setForm({
        merchant: extracted.merchant || "",
        amount: String(extracted.amount || ""),
        date: extracted.date || "",
        category: extracted.category || "",
        description: extracted.description || "",
      });
      setStep(STEPS.REVIEW);
    } catch {
      setStep(STEPS.UPLOAD);
    }
  }

  function handleDrop(e) {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFileSelect(file);
  }

  function validate() {
    const errs = {};
    REQUIRED_FIELDS.forEach((field) => {
      if (!form[field] || String(form[field]).trim() === "") {
        errs[field] = "This field is required";
      }
    });
    if (form.amount) {
      const amt = Number(form.amount);
      if (isNaN(amt)) {
        errs.amount = "Amount must be a number";
      } else if (amt > 10000) {
        errs.amount = "Maximum amount per claim is ₹10,000";
      }
    }
    setErrors(errs);
    return Object.keys(errs).length === 0;
  }

  async function handleSaveDraft() {
    setStep(STEPS.SUBMITTING);
    const claim = await createClaim({ ...form, currency: "INR" });
    navigate("/claims", { state: { toast: `Draft saved — ${claim.id}` } });
  }

  async function handleSubmit() {
    if (!validate()) return;
    setStep(STEPS.SUBMITTING);
    const claim = await createClaim({ ...form, currency: "INR" });
    await submitClaim(claim.id);
    setStep(STEPS.SUCCESS);
    setTimeout(() => navigate("/claims", { state: { toast: "Claim submitted successfully! 🎉" } }), 1600);
  }

  function handleFormChange(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
    if (errors[field]) setErrors((prev) => ({ ...prev, [field]: undefined }));
  }

  // ── Render ────────────────────────────────────────────────
  const today = new Date().toISOString().split("T")[0];

  return (
    <div className="page-content">
      {/* Back */}
      <button
        id="create-claim-back-btn"
        className="btn btn--ghost btn--sm back-btn"
        onClick={() => navigate(-1)}
      >
        <ArrowLeft size={15} strokeWidth={2} />
        Back
      </button>

      <div className="page-header page-header--compact">
        <div>
          <h1 className="page-header__title">Add Expense</h1>
          <p className="page-header__subtitle">
            Upload your receipt and we'll handle the rest.
          </p>
        </div>
      </div>

      <div className="create-claim-split">
        {/* ── Left Column: Form ── */}
        <div className="create-claim-col">
          <div className="card review-card">
            <div className="review-header">
              <h2 className="review-card__title">Expense Details</h2>
              <p className="review-card__subtitle">
                Fill in the details below. Upload a receipt to auto-fill.
              </p>
            </div>

            <form className="claim-form" onSubmit={(e) => e.preventDefault()}>
              {/* Merchant */}
              <div className={`form-group ${errors.merchant ? "form-group--error" : ""}`}>
                <label htmlFor="form-merchant" className="form-label">
                  Merchant <span className="required">*</span>
                </label>
                <input
                  id="form-merchant"
                  type="text"
                  className="form-input"
                  placeholder="e.g. Amazon, Uber"
                  value={form.merchant}
                  onChange={(e) => handleFormChange("merchant", e.target.value)}
                />
                {errors.merchant && <p className="form-error"><AlertCircle size={12} /> {errors.merchant}</p>}
              </div>

              {/* Amount + Date row */}
              <div className="form-row">
                <div className={`form-group ${errors.amount ? "form-group--error" : ""}`}>
                  <label htmlFor="form-amount" className="form-label">
                    Amount (₹) <span className="required">*</span>
                  </label>
                  <input
                    id="form-amount"
                    type="number"
                    className="form-input"
                    placeholder="0"
                    value={form.amount}
                    onChange={(e) => handleFormChange("amount", e.target.value)}
                    min="0"
                    max="10000"
                    step="0.01"
                  />
                  {errors.amount && <p className="form-error"><AlertCircle size={12} /> {errors.amount}</p>}
                </div>

                <div className={`form-group ${errors.date ? "form-group--error" : ""}`}>
                  <label htmlFor="form-date" className="form-label">
                    Expense Date <span className="required">*</span>
                  </label>
                  <input
                    id="form-date"
                    type="date"
                    className="form-input"
                    value={form.date}
                    max={today}
                    onChange={(e) => handleFormChange("date", e.target.value)}
                  />
                  {errors.date && <p className="form-error"><AlertCircle size={12} /> {errors.date}</p>}
                </div>
              </div>

              {/* Category */}
              <div className={`form-group ${errors.category ? "form-group--error" : ""}`}>
                <label htmlFor="form-category" className="form-label">
                  Category <span className="required">*</span>
                </label>
                <select
                  id="form-category"
                  className="form-input form-select"
                  value={form.category}
                  onChange={(e) => handleFormChange("category", e.target.value)}
                >
                  <option value="">Select a category…</option>
                  {EXPENSE_CATEGORIES.map((cat) => (
                    <option key={cat} value={cat}>{cat}</option>
                  ))}
                </select>
                {errors.category && <p className="form-error"><AlertCircle size={12} /> {errors.category}</p>}
              </div>

              {/* Description */}
              <div className="form-group">
                <label htmlFor="form-description" className="form-label">
                  Description <span className="optional">(optional)</span>
                </label>
                <textarea
                  id="form-description"
                  className="form-input form-textarea"
                  placeholder="Brief note about this expense…"
                  rows={3}
                  value={form.description}
                  onChange={(e) => handleFormChange("description", e.target.value)}
                />
              </div>

              {/* Manager (read-only) */}
              <div className="form-group form-group--readonly">
                <label className="form-label" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <User size={13} strokeWidth={1.75} />
                  Manager
                  <span title="Manager will be emailed with cc to Finance team" style={{ cursor: 'help', color: 'var(--text-muted)', display: 'inline-flex' }}>
                    <HelpCircle size={14} />
                  </span>
                </label>
                <div className="readonly-field">
                  <div className="manager-avatar manager-avatar--sm" aria-hidden="true">
                    {CURRENT_USER.manager.charAt(0)}
                  </div>
                  <span>{CURRENT_USER.manager}</span>
                  <span className="readonly-badge">Auto-assigned</span>
                </div>
              </div>

              {/* Actions moved to the right column */}
            </form>
          </div>
        </div>

        {/* ── Right Column: Upload / Analyzing ── */}
        <div className="create-claim-col">
          {step === STEPS.ANALYZING && (
            <div className="card analyzing-card">
              <div className="analyzing-state">
                <div className="analyzing-spinner">
                  <Loader2 size={36} strokeWidth={1.5} className="spin" />
                </div>
                <h2 className="analyzing-state__title">Analyzing receipt…</h2>
                <p className="analyzing-state__subtitle">
                  Extracting merchant, amount, and category from your receipt.
                </p>
                {uploadedFileName && (
                  <p className="analyzing-state__file">{uploadedFileName}</p>
                )}
              </div>
            </div>
          )}

          {step === STEPS.UPLOAD && (
            <div className="upload-card card">
              <section className="upload-section">
                <h2 className="upload-section__title">Upload receipt</h2>
                <div
                  className={`drop-zone ${dragOver ? "drop-zone--active" : ""}`}
                  onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                  onDragLeave={() => setDragOver(false)}
                  onDrop={handleDrop}
                  onClick={() => fileInputRef.current?.click()}
                  role="button"
                  tabIndex={0}
                  id="receipt-drop-zone"
                  aria-label="Upload receipt file"
                  onKeyDown={(e) => e.key === "Enter" && fileInputRef.current?.click()}
                >
                  <Upload size={32} strokeWidth={1.5} className="drop-zone__icon" />
                  <p className="drop-zone__primary">Drop your receipt here</p>
                  <p className="drop-zone__secondary">or click to browse — JPG, PNG, PDF</p>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/*,.pdf"
                    className="visually-hidden"
                    id="receipt-file-input"
                    onChange={(e) => handleFileSelect(e.target.files[0])}
                  />
                </div>
                {uploadedFileName ? (
                  <div style={{ marginTop: '16px' }}>
                    <p style={{fontSize: '13px', color: 'var(--text-h)', marginBottom: '12px', textAlign: 'center'}}>
                      Selected: <strong>{uploadedFileName}</strong>
                    </p>
                    <button
                      className="btn btn--secondary btn--full"
                      onClick={handleAnalyzeBill}
                    >
                      <FileText size={15} strokeWidth={2} />
                      Analyze Bill
                    </button>
                  </div>
                ) : (
                  <button
                    id="upload-receipt-btn"
                    className="btn btn--primary btn--full"
                    onClick={() => fileInputRef.current?.click()}
                  >
                    <Upload size={15} strokeWidth={2} />
                    Browse Files
                  </button>
                )}
              </section>
            </div>
          )}

          {(step === STEPS.REVIEW || step === STEPS.SUBMITTING || step === STEPS.SUCCESS) && (
            <div className="card review-file-card">
              <h2 className="upload-section__title" style={{ marginBottom: "16px" }}>Receipt</h2>
              {uploadedFileName ? (
                <div className="uploaded-file-info" style={{ padding: '16px', background: 'var(--accent-bg)', borderRadius: 'var(--radius)', border: '1px solid var(--accent-border)' }}>
                  <p style={{fontSize: '12px', fontWeight: '600', color: 'var(--accent)', textTransform: 'uppercase', marginBottom: '4px'}}>Current File</p>
                  <p style={{fontSize: '14px', color: 'var(--text-h)', wordBreak: 'break-all'}}>{uploadedFileName}</p>
                </div>
              ) : (
                <div className="uploaded-file-info" style={{ padding: '16px', background: 'var(--surface-2)', borderRadius: 'var(--radius)', border: '1px solid var(--border)' }}>
                   <p style={{fontSize: '14px', color: 'var(--text-muted)', textAlign: 'center'}}>No receipt uploaded.</p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* ── Bottom Section: Actions ── */}
      {(step === STEPS.REVIEW || step === STEPS.SUBMITTING || step === STEPS.SUCCESS) && (
        <div className="card bottom-actions" style={{ marginTop: '24px', display: 'flex', justifyContent: 'flex-end', gap: '12px', padding: '16px 24px' }}>
          <button
            id="save-draft-btn"
            type="button"
            className="btn btn--ghost"
            onClick={handleSaveDraft}
            disabled={step === STEPS.SUBMITTING || step === STEPS.SUCCESS}
          >
            Save Draft
          </button>
          <button
            id="submit-claim-btn"
            type="button"
            className="btn btn--primary"
            onClick={handleSubmit}
            disabled={step === STEPS.SUBMITTING || step === STEPS.SUCCESS}
          >
            {step === STEPS.SUCCESS ? (
              <>
                <Check size={15} strokeWidth={2.5} />
                Submitted!
              </>
            ) : step === STEPS.SUBMITTING ? (
              <>
                <Loader2 size={15} className="spin" />
                Submitting…
              </>
            ) : (
              "Submit Claim"
            )}
          </button>
        </div>
      )}
    </div>
  );
}
