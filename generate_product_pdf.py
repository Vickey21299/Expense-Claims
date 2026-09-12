import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super(NumberedCanvas, self).__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_header_footer(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_header_footer(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))

        # Header (pages 2+)
        if self._pageNumber > 1:
            self.drawString(54, 755, "AI-Powered Expense Claims & Forensic Verification System — Product Guide")
            self.setStrokeColor(colors.HexColor("#cbd5e1"))
            self.setLineWidth(0.5)
            self.line(54, 748, 558, 748)

        # Footer (all pages)
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.5)
        self.line(54, 45, 558, 45)
        
        self.drawString(54, 32, "Confidential — Internal Corporate Policy & Product Guide")
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(558, 32, page_str)
        self.restoreState()

def build_pdf(filename="Expense_Claims_Product_Guide.pdf"):
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()
    
    # Custom styles
    primary_color = colors.HexColor("#0f172a") # Slate 900
    accent_color = colors.HexColor("#2563eb")  # Blue 600
    text_color = colors.HexColor("#334155")    # Slate 700
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=primary_color,
        spaceAfter=6
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#64748b"),
        spaceAfter=14
    )
    
    h1_style = ParagraphStyle(
        'Heading1_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=accent_color,
        spaceBefore=12,
        spaceAfter=6,
        keepWithNext=True
    )
    
    h2_style = ParagraphStyle(
        'Heading2_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=primary_color,
        spaceBefore=8,
        spaceAfter=4,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'Body_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=14,
        textColor=text_color,
        spaceAfter=6
    )
    
    callout_style = ParagraphStyle(
        'Callout_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#1e293b")
    )
    
    table_cell = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11.5,
        textColor=text_color
    )
    
    table_cell_bold = ParagraphStyle(
        'TableCellBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11.5,
        textColor=primary_color
    )
    
    table_cell_header = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=colors.white
    )

    story = []

    # Title & Header
    story.append(Paragraph("AI-Powered Expense Claims System", title_style))
    story.append(Paragraph("Product Specification, Policy Limits, Architecture & Workflow Guide", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=accent_color, spaceAfter=12))

    # 1. Executive Summary
    story.append(Paragraph("1. Executive Summary & Product Mission", h1_style))
    story.append(Paragraph(
        "The <b>Expense Claims & Forensic Verification System</b> is an enterprise-grade corporate platform designed to eliminate fraudulent or duplicate out-of-pocket reimbursements while delivering a zero-friction experience for employees. "
        "By fusing <b>Google Gemini Vision OCR</b> with a multi-signal deterministic similarity engine and structured separation of duties between Managers and Financial Controllers, "
        "the system guarantees speed, mathematical precision, and regulatory compliance.",
        body_style
    ))
    
    # Highlights Box
    highlights_data = [
        [Paragraph("<b>Key Differentiators:</b><br/>"
                   "• <b>Gemini Vision AI:</b> Instant OCR line-item extraction from receipts (PDF, PNG, JPG).<br/>"
                   "• <b>Forensic Duplicate Engine:</b> Exact hash matches + Levenshtein merchant distance + date/amount variance.<br/>"
                   "• <b>Separation of Duties:</b> Managers evaluate business necessity; Finance evaluates cross-company duplication.<br/>"
                   "• <b>Terminal Paid State:</b> Immutable payment settlement via PaymentService (prevents double payout).", callout_style)]
    ]
    t_highlight = Table(highlights_data, colWidths=[504])
    t_highlight.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f1f5f9")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#cbd5e1")),
        ('PADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_highlight)
    story.append(Spacer(1, 10))

    # 2. Financial Limits & Policy Thresholds
    story.append(Paragraph("2. Financial Limits, Thresholds & Policy Rules", h1_style))
    story.append(Paragraph("Every claim is evaluated against deterministic organizational thresholds:", body_style))

    limits_data = [
        [Paragraph("Rule / Policy", table_cell_header), Paragraph("Value / Ceiling", table_cell_header), Paragraph("Type", table_cell_header), Paragraph("Description & Rationale", table_cell_header)],
        [Paragraph("Minimum Claim Amount", table_cell_bold), Paragraph("₹1.00", table_cell), Paragraph("Enforced", table_cell), Paragraph("Claims cannot be ₹0 or negative.", table_cell)],
        [Paragraph("Per-Claim Ceiling", table_cell_bold), Paragraph("₹10,000", table_cell), Paragraph("Policy Cap", table_cell), Paragraph("Standard limit for staff claims. Amounts above ₹10,000 require director escalation.", table_cell)],
        [Paragraph("Tax & Audit Threshold", table_cell_bold), Paragraph("₹5,000", table_cell), Paragraph("Mandate", table_cell), Paragraph("Claims > ₹5,000 require verified GST/Tax identification & item matching before clearance.", table_cell)],
        [Paragraph("Receipt Upload", table_cell_bold), Paragraph("Mandatory", table_cell), Paragraph("Enforced", table_cell), Paragraph("Valid receipt strictly required for all reimbursable claims.", table_cell)],
        [Paragraph("Stale Receipt Window", table_cell_bold), Paragraph("90 Days", table_cell), Paragraph("Rule", table_cell), Paragraph("Receipts older than 90 days are flagged as STALE_RECEIPT for manager inspection.", table_cell)],
        [Paragraph("Max File Size", table_cell_bold), Paragraph("10 MB", table_cell), Paragraph("Enforced", table_cell), Paragraph("Maximum allowable file size per receipt attachment.", table_cell)],
        [Paragraph("Allowed Formats", table_cell_bold), Paragraph("PDF, PNG, JPG, WEBP", table_cell), Paragraph("Enforced", table_cell), Paragraph("Strict MIME-type validation to prevent malicious uploads.", table_cell)],
        [Paragraph("Base Currency", table_cell_bold), Paragraph("INR (₹)", table_cell), Paragraph("Standard", table_cell), Paragraph("Base operating currency; foreign currencies normalized to INR.", table_cell)],
    ]
    t_limits = Table(limits_data, colWidths=[120, 74, 65, 245])
    t_limits.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), accent_color),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")]),
        ('PADDING', (0,0), (-1,-1), 4.5),
    ]))
    story.append(t_limits)
    story.append(Spacer(1, 12))

    # 3. Roles & Segregation of Duties
    story.append(Paragraph("3. Roles & Segregation of Duties", h1_style))
    roles_data = [
        [Paragraph("Role / User", table_cell_header), Paragraph("Primary Competency", table_cell_header), Paragraph("Allowed Actions & Constraints", table_cell_header)],
        [
            Paragraph("<b>Staff (Employee)</b><br/>Vickey Kumar (usr-001)", table_cell),
            Paragraph("Submits out-of-pocket expenses", table_cell),
            Paragraph("• Upload receipts & trigger Gemini OCR extraction.<br/>• Adjust line items before submitting.<br/>• <b>Cannot approve own claims or alter statuses.</b>", table_cell)
        ],
        [
            Paragraph("<b>Approving Manager</b><br/>Rahul Sharma (usr-mgr-001)", table_cell),
            Paragraph("Validates business context & expense necessity", table_cell),
            Paragraph("• Approve clean claims (routes to payment).<br/>• Confirm business context on FLAGGED claims.<br/>• Reject invalid claims with mandatory comment.<br/>• <b>Self-approval structurally blocked.</b>", table_cell)
        ],
        [
            Paragraph("<b>Financial Controller</b><br/>Anita Joshi (usr-fin-001)", table_cell),
            Paragraph("Adjudicates company-wide financial integrity", table_cell),
            Paragraph("• Inspect cross-company duplicate signals.<br/>• Clear financial exceptions with audit justification.<br/>• Execute simulated bank payouts (TXN-PAY-...).<br/>• <b>Cannot pay claims prior to READY_FOR_PAYMENT.</b>", table_cell)
        ]
    ]
    t_roles = Table(roles_data, colWidths=[130, 140, 234])
    t_roles.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), primary_color),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")]),
        ('PADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_roles)
    story.append(Spacer(1, 12))

    # 4. Lifecycle & State Machine
    story.append(Paragraph("4. End-to-End Lifecycle & State Machine", h1_style))
    story.append(Paragraph(
        "Claims follow a deterministic, dual-path state machine based on the automated verification score:",
        body_style
    ))

    flow_data = [
        [Paragraph("Phase", table_cell_header), Paragraph("State", table_cell_header), Paragraph("Path & Transition Event", table_cell_header)],
        [Paragraph("1. Ingestion", table_cell_bold), Paragraph("DRAFT", table_cell), Paragraph("Employee creates claim and uploads receipt. Gemini Vision auto-fills details.", table_cell)],
        [Paragraph("2. Submission", table_cell_bold), Paragraph("SUBMITTED", table_cell), Paragraph("Employee confirms details and submits. Automated Verification Engine executes.", table_cell)],
        [Paragraph("3A. Clean Path", table_cell_bold), Paragraph("CLEAN ➔ APPROVED", table_cell), Paragraph("Score < 40%. Direct to Manager. Manager approves ➔ READY_FOR_PAYMENT.", table_cell)],
        [Paragraph("3B. Flagged Path", table_cell_bold), Paragraph("FLAGGED", table_cell), Paragraph("Score >= 40% (duplicate risk). Requires dual review sign-off.", table_cell)],
        [Paragraph("4. Context Signoff", table_cell_bold), Paragraph("MANAGER_CONFIRMED", table_cell), Paragraph("Manager reviews duplicate evidence, confirms business legitimacy with required comment.", table_cell)],
        [Paragraph("5. Finance Clearance", table_cell_bold), Paragraph("READY_FOR_PAYMENT", table_cell), Paragraph("Finance reviews cross-department evidence, clears exception ➔ Queued for payout.", table_cell)],
        [Paragraph("6. Disbursement", table_cell_bold), Paragraph("PAID (Terminal)", table_cell), Paragraph("Finance executes payment. Payment reference logged. State is permanent and immutable.", table_cell)],
        [Paragraph("Exception", table_cell_bold), Paragraph("REJECTED", table_cell), Paragraph("Available at Manager or Finance stage with required written reason.", table_cell)],
    ]
    t_flow = Table(flow_data, colWidths=[90, 114, 300])
    t_flow.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#3b82f6")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")]),
        ('PADDING', (0,0), (-1,-1), 4.5),
    ]))
    story.append(t_flow)
    story.append(Spacer(1, 12))

    # 5. AI Verification & Forensic Engine Rules
    story.append(Paragraph("5. AI Verification & Forensic Engine Architecture", h1_style))
    story.append(Paragraph(
        "To maximize speed and minimize LLM API token consumption, verification is executed in 3 tiers:<br/>"
        "• <b>Tier 1 (Fast Retrieval):</b> Indexed database search for historical candidates matching merchant or date proximity.<br/>"
        "• <b>Tier 2 (Deterministic Scoring):</b> File SHA-256 hash comparison, Levenshtein merchant distance, exact date delta, and invoice number match.<br/>"
        "• <b>Tier 3 (Gemini Forensic Analysis):</b> Only triggered when similarity score is in the ambiguous/borderline zone (40% - 100%). Gemini generates duplicate risk percentage, risk classification (LOW / MEDIUM / HIGH), forensic explanation, and manager recommendations.",
        body_style
    ))
    story.append(Spacer(1, 6))

    # 6. Payment Execution & Guardrails
    story.append(Paragraph("6. Payment Execution & Settlement Guardrails", h1_style))
    story.append(Paragraph(
        "• <b>Provider Abstraction:</b> Built using <code>PaymentProvider</code> interface and <code>MockPaymentProvider</code> simulating instant UPI/NEFT banking settlement.<br/>"
        "• <b>Reference Generation:</b> Generates unique reference code: <code>TXN-PAY-{YYYYMMDD}-{HEX6}</code>.<br/>"
        "• <b>Terminal State Guardrail:</b> Attempting to pay an already <code>PAID</code> claim returns HTTP 409 Conflict.<br/>"
        "• <b>Prerequisite Guardrail:</b> Only claims in <code>READY_FOR_PAYMENT</code> status can be disbursed.",
        body_style
    ))
    story.append(Spacer(1, 6))

    # 7. SLA & Audit Trail
    story.append(Paragraph("7. SLA & Turnaround Duration Tracking", h1_style))
    story.append(Paragraph(
        "• <b>Immutable Log:</b> Every transition is recorded in <code>claim_status_history</code> with actor name, timestamps, and comments.<br/>"
        "• <b>Step SLA Metrics:</b> UI computes elapsed duration between every step (e.g. <code>+27s</code> draft to verification, <code>+1h 45m</code> submission to manager review).<br/>"
        "• <b>End-to-End Cycle Time:</b> Automatically calculates total turnaround time from creation to payout (e.g. <code>⚡ Turnaround: 2h 15m</code>).",
        body_style
    ))
    story.append(Spacer(1, 6))

    # 8. Future Work & Scalability Roadmap (1 to 100,000+ Users)
    story.append(Paragraph("8. Future Work & Scalability Roadmap (Scaling 1 to 100,000+ Users)", h1_style))
    story.append(Paragraph(
        "• <b>Production Code Hardening:</b> Enforce strict static typing (<code>mypy --strict</code>), ClamAV virus scanning for uploads, binary magic-byte MIME validation, and circuit breakers (<code>tenacity</code>) for third-party AI APIs.<br/>"
        "• <b>Observability & Grafana Telemetry:</b> Prometheus metrics exporter (RPS, error rate, p99 latency, DB pool saturation, Gemini token burn) paired with custom Grafana dashboards and OpenTelemetry distributed tracing.<br/>"
        "• <b>High-Concurrency Architecture:</b> Offload heavy OCR and forensic analysis to asynchronous worker queues (Celery/ARQ with Redis). Deploy PgBouncer connection pooling and read replicas for analytical queries.<br/>"
        "• <b>FinOps & Token Optimization:</b> Exact SHA-256 hash caching to bypass redundant Gemini API calls. Tiered gating ensures clean claims incur $0 LLM expense.<br/>"
        "• <b>Multi-Tier Rate Limiting:</b> Redis token-bucket rate limiters (per-IP, per-user upload quotas, AI endpoint burst caps) fronted by Cloudflare WAF.<br/>"
        "• <b>Enterprise IAM & RBAC:</b> Transition from mock auth to enterprise SSO (OAuth 2.0 / SAML 2.0 / Entra ID / Google Workspace) with cryptographically signed JWTs.<br/>"
        "• <b>Automated Load & Stress Testing:</b> Locust & k6 test suites simulating 1,000 to 100,000 concurrent active users to validate sub-300ms p99 latency and zero data-loss resilience.<br/>"
        "• <b>Banking & ERP Integrations:</b> Direct webhook integration with corporate disbursement rails (RazorpayX, Stripe Treasury, IMPS/NEFT) and automated ERP sync (SAP, Oracle NetSuite, QuickBooks).",
        body_style
    ))

    # Build Document
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Successfully generated {filename}")

if __name__ == "__main__":
    build_pdf()
