from decimal import Decimal

from app.domain.finance import ApprovalRole, PolicyReference

AP_CORE = PolicyReference(
    document_id="FIN-POL-001", version="4.2", section="Core controls", rule_id="AP_CORE"
)
THREE_WAY = PolicyReference(
    document_id="FIN-POL-002", version="3.0", section="Tolerances", rule_id="THREE_WAY"
)
AUTHORITY = PolicyReference(
    document_id="FIN-POL-003", version="6.0", section="Monetary limits", rule_id="CURRENT_DFA"
)
VENDOR = PolicyReference(
    document_id="FIN-POL-004", version="5.1", section="Vendor controls", rule_id="VENDOR_CONTROL"
)
DUPLICATE = PolicyReference(
    document_id="FIN-POL-005", version="2.4", section="Duplicate detection", rule_id="DUPLICATE"
)
FX = PolicyReference(
    document_id="FIN-POL-006", version="2.0", section="Currency", rule_id="CURRENCY"
)
EXCEPTIONS = PolicyReference(
    document_id="FIN-POL-007", version="3.1", section="Exceptions", rule_id="EXCEPTION"
)
MANUAL_PAYMENT = PolicyReference(
    document_id="FIN-POL-009", version="1.8", section="Manual payments", rule_id="MANUAL_PAYMENT"
)
FRAUD = PolicyReference(
    document_id="FIN-POL-012", version="2.2", section="Fraud indicators", rule_id="FRAUD"
)

GOODS_ABSOLUTE_VARIANCE = Decimal("50.00")
GOODS_PERCENT_VARIANCE = Decimal("0.01")
SERVICE_ABSOLUTE_VARIANCE = Decimal("100.00")
SERVICE_PERCENT_VARIANCE = Decimal("0.02")
FREIGHT_TOLERANCE = Decimal("75.00")
PROBABLE_DUPLICATE_DAYS = 14
PROBABLE_DUPLICATE_AMOUNT_PERCENT = Decimal("0.005")
BANK_CHANGE_LOOKBACK_DAYS = 30
NEW_VENDOR_LOOKBACK_DAYS = 90

AUTHORITY_BANDS = (
    (Decimal("10000.00"), ApprovalRole.COST_CENTRE_MANAGER),
    (Decimal("50000.00"), ApprovalRole.DEPARTMENT_DIRECTOR),
    (Decimal("250000.00"), ApprovalRole.EXECUTIVE_DIRECTOR),
    (Decimal("1000000.00"), ApprovalRole.CHIEF_FINANCIAL_OFFICER),
)
