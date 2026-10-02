from typing import Any

SENSITIVE_KEY_FRAGMENTS = ("bank", "account", "credential", "password", "secret", "signature")


def redact_sensitive(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "[REDACTED]"
            if any(fragment in key.lower() for fragment in SENSITIVE_KEY_FRAGMENTS)
            else redact_sensitive(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_sensitive(item) for item in value]
    return value
