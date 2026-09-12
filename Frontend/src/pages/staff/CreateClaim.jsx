import { useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { Upload, FileText, Check, Loader2, ArrowLeft, User, AlertCircle, HelpCircle, Sparkles } from "lucide-react";
import { analyzeReceipt, createClaim, submitClaim, uploadReceipt, EXPENSE_CATEGORIES } from "../../services/api";
import { CURRENT_USER } from "../../data/users";

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
  const [form, setForm] = useState(EMPTY_FORM);
  const [errors, setErrors] = useState({});
  const [dragOver, setDragOver] = useState(false);
  const [uploadedFileName, setUploadedFileName] = useState(null);
  const [selectedFile, setSelectedFile] = useState(null);
  const [analyzedLineItems, setAnalyzedLineItems] = useState([]);
  const [analysisNotice, setAnalysisNotice] = useState(null);

  // ── Handlers ──────────────────────────────────────────────

  function handleFileSelect(file) {
    if (!file) return;
    setUploadedFileName(file.name);
    setSelectedFile(file);
    setAnalysisNotice(null);
  }

  async function handleAnalyzeBill() {
    if (!selectedFile) return;
    setStep(STEPS.ANALYZING);
    setAnalysisNotice(null);
    try {
      const extracted = await analyzeReceipt(selectedFile);
      setForm({
        merchant: extracted.merchant || "",
        amount: extracted.amount !== null && extracted.amount !== undefined ? String(extracted.amount) : "",
        date: extracted.date || "",
        category: extracted.category || "",
        description: extracted.description || "",
      });
      if (Array.isArray(extracted.line_items) && extracted.line_items.length > 0) {
        setAnalyzedLineItems(extracted.line_items);
      }
      setAnalysisNotice("Receipt analyzed with Gemini AI! Please review the extracted fields.");
      setStep(STEPS.REVIEW);
    } catch (err) {
      console.warn("AI extraction warning:", err);
      setAnalysisNotice("Automatic extraction was unavailable, but you can fill in details manually.");
      setStep(STEPS.REVIEW);
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
      } else if (amt > 200000) {
        errs.amount = "Maximum amount per claim is ₹2,00,000";
      }
    }
    setErrors(errs);
    return Object.keys(errs).length === 0;
  }

  async function handleSaveDraft() {
    try {
      setStep(STEPS.SUBMITTING);
      const claim = await createClaim({ ...form, currency: "INR" });
      if (selectedFile && claim.id) {
        try {
          await uploadReceipt(claim.id, selectedFile);
        } catch (uploadErr) {
          console.warn("Receipt upload warning:", uploadErr);
        }
      }
      navigate("/claims", { state: { toast: `Draft saved — ${claim.claimRef || claim.claim_ref || claim.id}` } });
    } catch (err) {
      console.error("Save draft error:", err);
      setErrors((prev) => ({ ...prev, form: err.message || "Failed to save draft" }));
      setStep(STEPS.REVIEW);
    }
  }

  async function handleSubmit() {
    if (!validate()) return;
    try {
      setStep(STEPS.SUBMITTING);
      const claim = await createClaim({ ...form, currency: "INR" });
      if (selectedFile && claim.id) {
        try {
          await uploadReceipt(claim.id, selectedFile);
        } catch (uploadErr) {
          console.warn("Receipt upload warning:", uploadErr);
        }
      }
      await submitClaim(claim.id);
      setStep(STEPS.SUCCESS);
      setTimeout(() => {
        navigate("/claims", { state: { toast: `Claim ${claim.claimRef || claim.claim_ref || ""} submitted successfully! 🎉` } });
      }, 1400);
    } catch (err) {
      console.error("Submit claim error:", err);
      setErrors((prev) => ({ ...prev, form: err.message || "Failed to submit claim" }));
      setStep(STEPS.REVIEW);
    }
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
              {analysisNotice && (
                <div style={{
                  marginTop: "12px",
                  padding: "10px 14px",
                  borderRadius: "8px",
                  background: "rgba(99, 102, 241, 0.1)",
                  border: "1px solid rgba(99, 102, 241, 0.25)",
                  color: "var(--accent)",
                  fontSize: "13px",
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                }}>
                  <Sparkles size={16} />
                  <span>{analysisNotice}</span>
                </div>
              )}
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

              {analyzedLineItems.length > 0 && (
                <div style={{ marginTop: '16px' }}>
                  <p style={{ fontSize: '12px', fontWeight: '600', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '8px' }}>
                    AI-Detected Items ({analyzedLineItems.length})
                  </p>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', maxHeight: '180px', overflowY: 'auto' }}>
                    {analyzedLineItems.map((item, idx) => (
                      <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', padding: '6px 10px', background: 'var(--surface-2)', borderRadius: '6px' }}>
                        <span style={{ color: 'var(--text-h)' }}>{item.description || `Item #${idx + 1}`}</span>
                        <span style={{ fontWeight: 600, color: 'var(--text-h)' }}>
                          ₹{item.amount != null ? Number(item.amount).toLocaleString('en-IN') : '—'}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* ── Bottom Section: Actions ── */}
      {(step === STEPS.REVIEW || step === STEPS.SUBMITTING || step === STEPS.SUCCESS) && (
        <div className="card bottom-actions" style={{ marginTop: '24px', display: 'flex', flexDirection: 'column', gap: '12px', padding: '16px 24px' }}>
          {errors.form && (
            <div style={{ padding: '10px 14px', borderRadius: '6px', background: 'rgba(239, 68, 68, 0.1)', color: 'var(--danger)', fontSize: '13px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <AlertCircle size={15} />
              <span>{errors.form}</span>
            </div>
          )}
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
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
        </div>
      )}
    </div>
  );
}
