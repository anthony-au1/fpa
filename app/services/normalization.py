import re
import unicodedata


def normalize_invoice_reference(value: str) -> str:
    """Normalize case and whitespace only; punctuation remains significant for exact matches."""
    return " ".join(unicodedata.normalize("NFKC", value).upper().split())


def punctuation_insensitive_reference(value: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", normalize_invoice_reference(value))
