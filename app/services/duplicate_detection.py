from app.domain.finance import (
    DuplicateFinding,
    DuplicateMatchType,
    InvoiceEvidence,
    InvoiceHistoryStatus,
)
from app.services.normalization import (
    normalize_invoice_reference,
    punctuation_insensitive_reference,
)
from app.services.policy_rules import PROBABLE_DUPLICATE_AMOUNT_PERCENT, PROBABLE_DUPLICATE_DAYS
from app.tools.contracts import InvoiceHistoryRecord


def detect_duplicates(
    invoice: InvoiceEvidence, history: list[InvoiceHistoryRecord]
) -> list[DuplicateFinding]:
    findings: list[DuplicateFinding] = []
    exact_reference = normalize_invoice_reference(invoice.invoice_reference)
    fuzzy_reference = punctuation_insensitive_reference(invoice.invoice_reference)
    for record in history:
        exact_fields = [
            record.vendor_id == invoice.vendor_id,
            normalize_invoice_reference(record.invoice_reference) == exact_reference,
            record.currency == invoice.currency,
            record.amount == invoice.gross_amount,
        ]
        if all(exact_fields):
            findings.append(
                DuplicateFinding(
                    match_type=DuplicateMatchType.EXACT,
                    matched_record_id=record.stable_id,
                    history_status=record.status,
                    matched_fields=[
                        "vendor_id",
                        "normalized_invoice_reference",
                        "currency",
                        "gross_amount",
                    ],
                    signals=[],
                )
            )
            continue
        signals: list[str] = []
        if punctuation_insensitive_reference(record.invoice_reference) == fuzzy_reference:
            signals.append("punctuation_normalized_reference")
        if abs((record.invoice_date - invoice.invoice_date).days) <= PROBABLE_DUPLICATE_DAYS:
            signals.append("invoice_date_proximity")
        if (
            invoice.gross_amount
            and abs(record.amount - invoice.gross_amount) / invoice.gross_amount
            < PROBABLE_DUPLICATE_AMOUNT_PERCENT
        ):
            signals.append("small_amount_variance")
        if record.purchase_order_id and record.purchase_order_id == invoice.purchase_order_id:
            signals.append("same_purchase_order")
        if (
            record.attachment_fingerprint
            and record.attachment_fingerprint == invoice.attachment_fingerprint
        ):
            signals.append("attachment_fingerprint")
        anchor = {"punctuation_normalized_reference", "attachment_fingerprint"}
        if len(signals) >= 2 and anchor.intersection(signals):
            findings.append(
                DuplicateFinding(
                    match_type=DuplicateMatchType.PROBABLE,
                    matched_record_id=record.stable_id,
                    history_status=record.status,
                    matched_fields=[],
                    signals=signals,
                )
            )
    return findings


def has_blocking_exact_duplicate(findings: list[DuplicateFinding]) -> bool:
    return any(
        item.match_type is DuplicateMatchType.EXACT
        and item.history_status in {InvoiceHistoryStatus.PAID, InvoiceHistoryStatus.POSTED}
        for item in findings
    )
