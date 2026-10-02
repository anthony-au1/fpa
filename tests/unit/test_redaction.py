from app.observability.redaction import redact_sensitive


def test_sensitive_keys_are_redacted_recursively() -> None:
    result = redact_sensitive({"bank_account": "1234", "nested": {"password": "x", "ok": 1}})
    assert result == {
        "bank_account": "[REDACTED]",
        "nested": {"password": "[REDACTED]", "ok": 1},
    }
