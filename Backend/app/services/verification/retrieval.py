"""
app/services/verification/retrieval.py
Targeted database-side candidate retrieval for expense claim verification.
Never loads the whole claims table into memory.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from app.core.database import supabase
from app.core.logging import get_logger
from app.services.verification.config import verification_config

logger = get_logger(__name__)


def retrieve_candidates(
    claim_id: str,
    target_claim: dict[str, Any],
    target_extracted: dict[str, Any] | None,
    target_doc: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """
    Retrieve relevant historical claims from the full verification dataset
    using database-side indexed filters (checksum, invoice, amount/date window, merchant).
    Returns a list of candidate dicts containing claim, extracted, and document data.
    """
    candidate_ids: set[str] = set()

    # 1. Exact document checksum matches
    checksum = target_doc.get("checksum") if target_doc else None
    if checksum:
        try:
            res = (
                supabase.table("claim_documents")
                .select("claim_id")
                .eq("checksum", checksum)
                .neq("claim_id", claim_id)
                .limit(verification_config.MAX_CANDIDATES)
                .execute()
            )
            for row in res.data or []:
                candidate_ids.add(row["claim_id"])
        except Exception as e:
            logger.warning(f"[Retrieval] Checksum query warning: {e}")

    # 2. Exact invoice number matches
    invoice_number = None
    if target_extracted and target_extracted.get("invoice_number"):
        invoice_number = str(target_extracted["invoice_number"]).strip()
    if invoice_number:
        try:
            res = (
                supabase.table("claim_extracted_data")
                .select("claim_id")
                .eq("invoice_number", invoice_number)
                .neq("claim_id", claim_id)
                .limit(verification_config.MAX_CANDIDATES)
                .execute()
            )
            for row in res.data or []:
                candidate_ids.add(row["claim_id"])
        except Exception as e:
            logger.warning(f"[Retrieval] Invoice query warning: {e}")

    # 3. Amount & Date range matches
    amt = target_claim.get("amount") or (target_extracted.get("total") if target_extracted else None)
    target_date_val = target_claim.get("claim_date") or (target_extracted.get("transaction_date") if target_extracted else None)

    try:
        amount_num = float(amt) if amt is not None else None
    except (ValueError, TypeError):
        amount_num = None

    if amount_num and amount_num > 0:
        pct = verification_config.RETRIEVAL_AMOUNT_PCT
        min_amt = round(amount_num * (1.0 - pct), 2)
        max_amt = round(amount_num * (1.0 + pct), 2)

        try:
            q = (
                supabase.table("claims")
                .select("id")
                .gte("amount", min_amt)
                .lte("amount", max_amt)
                .neq("id", claim_id)
            )

            # If date is available, filter within date window
            if target_date_val:
                try:
                    d = (
                        date.fromisoformat(str(target_date_val)[:10])
                        if isinstance(target_date_val, str)
                        else target_date_val
                    )
                    window = timedelta(days=verification_config.RETRIEVAL_DATE_WINDOW_DAYS)
                    d_min = (d - window).isoformat()
                    d_max = (d + window).isoformat()
                    q = q.gte("claim_date", d_min).lte("claim_date", d_max)
                except Exception:
                    pass

            res = q.limit(verification_config.MAX_CANDIDATES).execute()
            for row in res.data or []:
                candidate_ids.add(row["id"])
        except Exception as e:
            logger.warning(f"[Retrieval] Amount/date query warning: {e}")

    # 4. Merchant name matches
    merchant = target_claim.get("merchant") or (
        target_extracted.get("merchant_normalized") if target_extracted else None
    )
    if merchant and len(str(merchant).strip()) >= 3:
        clean_merchant = str(merchant).strip()
        try:
            res = (
                supabase.table("claims")
                .select("id")
                .ilike("merchant", f"%{clean_merchant}%")
                .neq("id", claim_id)
                .limit(verification_config.MAX_CANDIDATES)
                .execute()
            )
            for row in res.data or []:
                candidate_ids.add(row["id"])
        except Exception as e:
            logger.warning(f"[Retrieval] Merchant query warning: {e}")

    if not candidate_ids:
        return []

    # Limit to maximum candidates
    selected_ids = list(candidate_ids)[: verification_config.MAX_CANDIDATES]

    # Fetch full candidate records in 1 single joined query using PostgREST resource embedding
    try:
        joined_res = (
            supabase.table("claims")
            .select("*, claim_extracted_data(*), claim_documents(id, checksum, file_name)")
            .in_("id", selected_ids)
            .execute()
        )

        candidates = []
        for c in joined_res.data or []:
            ext_list = c.get("claim_extracted_data") or []
            doc_list = c.get("claim_documents") or []
            candidates.append({
                "claim": c,
                "extracted": ext_list[0] if ext_list else None,
                "document": doc_list[0] if doc_list else None,
            })

        logger.info(
            f"[Retrieval] Fetched {len(candidates)} complete candidates in 1 joined query for claim_id={claim_id}"
        )
        return candidates

    except Exception as e:
        logger.error(f"[Retrieval] Failed fetching candidate details: {e}")
        return []
