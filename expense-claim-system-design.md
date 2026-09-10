# Expense Claim System — Design Documentation

**Status:** MVP design frozen. Implementation not yet started against this version.
**Purpose of this document:** record not just the final design, but why it changed shape — so a future reviewer (including a future us) can see which decisions were deliberate trade-offs versus gaps, and doesn't have to re-litigate settled questions.

---

## 1. The problem, restated

Staff spend their own money on travel, meals, supplies, taxis — then claim it back. Manager signs off, finance pays at month-end. Every company has a version of this, and it's painful because filing a claim takes longer than the thing it's claiming.

Four requirements were given as fixed constraints, not suggestions:

1. Managers file claims too, and must never approve their own.
2. A paid claim is finished — it must not go backwards.
3. The same receipt gets submitted twice — sometimes same day, sometimes three weeks later, sometimes reworded. Finance has paid duplicates before and this must stop.
4. Finance needs a month-end view: who spent what, by category, who's over limit.
5. Filing should be low-friction — paste the receipt, the system structures it, the person confirms or corrects before it goes anywhere.

---

## 2. How we started: a single-pass design

The first design was a straightforward 4-state machine:

```
SUBMITTED → APPROVED → PAID   (terminal)
     ↓
 REJECTED → SUBMITTED (resubmit)
```

Rules enforced server-side, not just in the UI:
- Self-approval blocked by comparing submitter ID to approver ID on every transition endpoint.
- A manager with no manager above them (a top-level manager, or founder-adjacent role) routed to Finance for approval instead of a peer — an edge case the brief didn't specify, made explicit rather than left to crash or silently self-approve.
- Duplicate detection ran once, at submission, in two tiers: an exact hash match on receipt text, and a fuzzy match (amount ±5%, date within 21 days, text similarity above a threshold). Neither blocked submission — both flagged the claim for the manager at approval and for finance again at payout.
- Receipt parsing was rule-based first (regex for amount/date, keyword map for category), with an LLM fallback stubbed for fields the rules couldn't confidently extract.

This version was built and tested end-to-end (self-approval block, terminal-payment enforcement, and duplicate detection all verified against adversarial test cases — see §6). It worked. But it had a structural flaw that surfaced once we started asking who actually *uses* each signal.

**The flaw:** the manager was doing two unrelated jobs at once — verifying the claim was a real, legitimate business expense, *and* being shown a duplicate-similarity flag they had no training or cross-team visibility to evaluate. Finance, the only role with visibility across all employees and all time, wasn't structurally positioned to be the authority on the thing only they could actually see.

---

## 3. How the design changed: separating who verifies what

The correction: split verification into two genuinely different competencies, owned by the two roles equipped to exercise them.

| Question | Who answers it | Why them |
|---|---|---|
| "Is this a real, legitimate expense?" | Manager | Has direct knowledge of the person and the work — knows if the client dinner actually happened |
| "Is this a repeat of something already claimed?" | Finance (system-assisted) | Only role with visibility across *all* employees and *all* history — a manager only sees their own team |

This produced a cleaner principle, stated explicitly so it can be checked against any future change to the flow:

> **The verification engine detects anomalies. The manager validates business context. Finance adjudicates financial anomalies. Finance executes payment.**

Each role gets exactly the kind of judgment it's actually positioned to make, and no role is asked to rubber-stamp a decision it can't meaningfully evaluate.

### 3.1 Where duplicate-checking runs, and why it isn't one checkpoint

Several placements were considered and rejected before landing on the current one:

- **Only at finance, after approval** — correct in principle (finance is the right authority) but wasteful: an obviously duplicate claim still consumes a manager's approval cycle before anyone catches it.
- **Only at submission (staff-facing)** — catches honest, same-session mistakes cheaply, but relies on the employee self-reporting a duplicate correctly. The brief explicitly describes the harder case (reworded, three weeks later) that a naive same-session check would miss — this can't be the *only* check without recreating the exact hole finance already fell into.
- **Authoritative check at submission, using finance's full dataset, shown live to the employee** — this is what got adopted. It's the earliest point with full information (amount, date, text, employee identity) and the cheapest point to stop a duplicate — before it wastes a manager's time. The employee is also the person best positioned to resolve an ambiguous match on the spot ("no, that was a different trip").

The resolution mechanism matters as much as the timing: a flagged match does **not** hard-block submission. Blocking on a probabilistic match risks stopping an honest, different expense that happens to resemble another — recurring taxi routes, team lunches at the same restaurant, same-amount recurring costs. The employee sees the match and can proceed anyway; that override travels with the claim as a flag, not as a silently resolved non-issue.

### 3.2 Why the LLM only runs on borderline cases

Cheap, deterministic similarity scoring (amount tolerance, date window, text token overlap) handles the large majority of comparisons — most claims are trivially distinct or trivially identical. The LLM is reserved for the ambiguous middle: cases the threshold can't confidently resolve either way. This is a cost and reliability decision, not a modeling preference — paying LLM latency and cost on every claim, including the 80% a regex and a similarity score settle for free, buys nothing and adds a new failure mode (misread amounts, hallucinated matches) to cases that didn't need it.

### 3.3 Why a flagged claim needs two *separate* signatures, not one shared approval

An early version of this branch let the manager see the duplicate evidence and clear it themselves as part of approval. This was rejected for a specific reason: a similarity score and an LLM's reasoning trail are not something a manager is equipped to adjudicate — they can confirm *the trip happened*, not *whether a 94% similarity match is a coincidence or a real duplicate*. Handing them that decision doesn't distribute judgment, it just relocates an underqualified veto.

The fix: a flagged claim requires the manager to confirm business context, **and independently** requires finance to adjudicate the anomaly — two separate responsibilities, not two people approving the same thing.

### 3.4 Why the state names matter, not just the flow

An early version of the flagged path collapsed back into the same `APPROVED` status the clean path uses:

```
FLAGGED → APPROVED → PAID        ✗ — indistinguishable from a clean approval after the fact
```

This was caught and corrected before being adopted, because it silently destroys the audit trail: a reviewer looking at a paid claim later cannot tell whether it went through extra scrutiny or sailed through untouched. The adopted version keeps the flagged path's states distinct all the way through:

```
FLAGGED → MANAGER_CONFIRMED → FINANCE_REVIEW → FINANCE_CLEARED → READY_FOR_PAYMENT
```

If a duplicate is ever paid by mistake, this state trail directly answers "who decided what, in what order" — which is the actual purpose of separating the states, not a stylistic preference.

---

## 4. Current state: the frozen MVP design

### 4.1 Org structure

Tree-structured hierarchy. Every user (staff or manager) has a parent in the chain, up to founder. A user can be staff and manager simultaneously — managers file claims through the same path staff use.

### 4.2 Full flow

```
Employee submits (amount + receipt text)
        ↓
AI / rule-based receipt parsing → structured claim, shown back for confirmation
        ↓
Verification engine
  · candidate retrieval (this employee, and cross-employee, cross-time)
  · similarity scoring (amount, date, text)
  · LLM analysis — only when the score is borderline
        ↓
   ┌────┴────┐
 CLEAN     FLAGGED
   │          │
   │     Manager review → confirms business context → MANAGER_CONFIRMED
   │          │
   │     Finance review → adjudicates the anomaly independently → FINANCE_CLEARED
   │          │
   └────┬─────┘
        ↓
  Manager review (clean path: single signoff)
        ↓
   READY_FOR_PAYMENT
        ↓
     PAID (terminal — no transition leaves this state)

Reject is available at: manager review (either path), or finance review (flagged path)
```

### 4.3 Rules carried through unchanged since the first version

- Self-approval is structurally blocked — checked against actual submitter/approver identity on every transition, not hidden in a UI.
- `PAID` has no code path leading out of it. Corrections happen via a new, separate claim — never by mutating history.
- A manager with no manager above them routes to finance for approval.
- Receipt parsing is shown back to the employee before submission; they can correct any field.

### 4.4 The principle this design is checked against

> The verification engine detects anomalies; the manager validates business context; finance adjudicates financial anomalies; finance executes payment.
>
> Clean claims take the fast path. Flagged claims require dual human review, with separate responsibilities rather than two people approving the same thing.

Any future change to the flow should be checked against this sentence before being adopted.

---

## 5. Known gaps — explicitly parked, not solved

These were identified during design review and deliberately deferred rather than papered over. Each one, if it fails silently in production, will look like a variant of the original "finance paid twice" problem — that's the reason they're listed here instead of quietly dropped.

1. **Segregation of duties inside finance.** `FINANCE_REVIEW → FINANCE_CLEARED → READY_FOR_PAYMENT` doesn't currently require a different person to clear the anomaly than the one who executes payment. The same single point of failure the manager/finance split was originally meant to avoid could re-appear entirely inside finance.
2. **Reject-from-`MANAGER_CONFIRMED` is undefined.** If a manager looks at a flagged claim and doesn't recognize it, where does that outcome go — straight to rejected, or does finance still see it as a closed loop? A manager's non-recognition combined with a system-flagged anomaly is a stronger signal than either alone; letting it vanish silently loses that signal.
3. **Where policy checks (monthly limits, category rules, receipt-required thresholds) plug in.** Currently `CLEAN`/`FLAGGED` is scoped to duplicate-similarity only. Whether policy violations route through the same dual-review branch or surface later in a finance report is undecided — and if it's the latter, that's a materially weaker control than duplicates get, which may or may not be intentional.
4. **Staleness / escalation.** No mechanism yet for a claim stuck at `MANAGER_CONFIRMED` or `FINANCE_REVIEW` because a reviewer is slow or unavailable. A flagged claim currently has two sequential human checkpoints with no timeout — directly in tension with the original "shouldn't take longer than the coffee" goal.
5. **LLM input/output contract.** Candidate set size and scope (this employee only vs. cross-org), output format (confidence score vs. reasoning trail vs. named candidate match), and cost controls at volume are not yet specified.

---

## 6. What's been verified so far

The first-version design (§2) was implemented and tested against adversarial cases before the design evolved to the current version:

- Self-approval attempt → blocked.
- Wrong-approver attempt (a manager who isn't the submitter's direct manager) → blocked.
- Legitimate approval → payment → second payment attempt on the same claim → blocked (terminal state holds).
- Top-level manager (no manager above them) → claim correctly routed to and approved by finance.
- Duplicate detection: an exact resubmission was caught; a reworded near-duplicate was initially **missed** due to a currency-suffix parsing bug and an overly strict similarity threshold — both were found by testing, not by inspection, and fixed. A genuinely different expense with a similar amount was confirmed **not** flagged, which matters as much as catching the true positive.

The current (§4) design has not yet been implemented — the state machine, dual-review branch, and verification engine described here are the target for the next build pass, not a description of running code.
