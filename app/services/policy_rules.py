from decimal import Decimal

from app.domain.finance import ApprovalRole, PolicyReference

AP_MINIMUM_EVIDENCE = PolicyReference(
    document_id="FIN-POL-001",
    version="3.2",
    section="2. Minimum evidence",
    rule_id="AP_MINIMUM_EVIDENCE",
)
AP_SEGREGATION_OF_DUTIES = PolicyReference(
    document_id="FIN-POL-001",
    version="3.2",
    section="4. Segregation of duties",
    rule_id="AP_SEGREGATION_OF_DUTIES",
)
AP_REQUIRED_CHECKS = PolicyReference(
    document_id="FIN-POL-001",
    version="3.2",
    section="5. Required checks",
    rule_id="AP_REQUIRED_CHECKS",
)
THREE_WAY_MATCHING = PolicyReference(
    document_id="FIN-POL-002",
    version="2.4",
    section="1. Matching basis",
    rule_id="THREE_WAY_MATCHING",
)
THREE_WAY_TOLERANCES = PolicyReference(
    document_id="FIN-POL-002",
    version="2.4",
    section="2. Tolerances",
    rule_id="THREE_WAY_TOLERANCES",
)
THREE_WAY_MISSING_RECEIPT = PolicyReference(
    document_id="FIN-POL-002",
    version="2.4",
    section="4. Missing receipt",
    rule_id="THREE_WAY_MISSING_RECEIPT",
)
AUTHORITY_GENERAL = PolicyReference(
    document_id="FIN-POL-003",
    version="4.0",
    section="1. General rules",
    rule_id="AUTHORITY_GENERAL",
)
AUTHORITY_LIMITS = PolicyReference(
    document_id="FIN-POL-003",
    version="4.0",
    section="2. Standard operating expenditure",
    rule_id="AUTHORITY_LIMITS",
)
AUTHORITY_HIGH_RISK = PolicyReference(
    document_id="FIN-POL-003",
    version="4.0",
    section="3. Higher-risk transactions",
    rule_id="AUTHORITY_HIGH_RISK",
)
VENDOR_BANK_CHANGES = PolicyReference(
    document_id="FIN-POL-004",
    version="5.1",
    section="2. Bank-account changes",
    rule_id="VENDOR_BANK_CHANGES",
)
VENDOR_STATUS = PolicyReference(
    document_id="FIN-POL-004",
    version="5.1",
    section="4. Vendor status",
    rule_id="VENDOR_STATUS",
)
DUPLICATE_DETECTION = PolicyReference(
    document_id="FIN-POL-005",
    version="2.8",
    section="1. Duplicate detection",
    rule_id="DUPLICATE_DETECTION",
)
DUPLICATE_OUTCOMES = PolicyReference(
    document_id="FIN-POL-005",
    version="2.8",
    section="2. Outcomes",
    rule_id="DUPLICATE_OUTCOMES",
)
FRAUD_INDICATORS = PolicyReference(
    document_id="FIN-POL-005",
    version="2.8",
    section="3. Fraud indicators",
    rule_id="FRAUD_INDICATORS",
)
EARLY_MANUAL_PAYMENTS = PolicyReference(
    document_id="FIN-POL-006",
    version="3.0",
    section="3. Early and manual payments",
    rule_id="EARLY_MANUAL_PAYMENTS",
)
EXCEPTION_CATEGORIES = PolicyReference(
    document_id="FIN-POL-007",
    version="1.9",
    section="1. Exception categories",
    rule_id="EXCEPTION_CATEGORIES",
)
FX_CURRENCY_AGREEMENT = PolicyReference(
    document_id="FIN-POL-009",
    version="1.6",
    section="1. Currency agreement",
    rule_id="FX_CURRENCY_AGREEMENT",
)
FX_CONVERSION = PolicyReference(
    document_id="FIN-POL-009",
    version="1.6",
    section="2. Conversion",
    rule_id="FX_CONVERSION",
)
FX_OVERSEAS_ACCOUNTS = PolicyReference(
    document_id="FIN-POL-009",
    version="1.6",
    section="4. Overseas accounts",
    rule_id="FX_OVERSEAS_ACCOUNTS",
)

GOODS_ABSOLUTE_VARIANCE = Decimal("50.00")
GOODS_PERCENT_VARIANCE = Decimal("0.01")
SERVICE_ABSOLUTE_VARIANCE = Decimal("100.00")
SERVICE_PERCENT_VARIANCE = Decimal("0.02")
PROBABLE_DUPLICATE_DAYS = 14
PROBABLE_DUPLICATE_AMOUNT_PERCENT = Decimal("0.005")
NEW_VENDOR_DAYS = 30
FRAUD_ESCALATION_INDICATOR_COUNT = 2

AUTHORITY_BANDS = (
    (Decimal("10000.00"), ApprovalRole.COST_CENTRE_MANAGER),
    (Decimal("50000.00"), ApprovalRole.DEPARTMENT_DIRECTOR),
    (Decimal("250000.00"), ApprovalRole.EXECUTIVE_DIRECTOR),
    (Decimal("1000000.00"), ApprovalRole.CHIEF_FINANCIAL_OFFICER),
)

# Test/audit guard only: corpus Markdown never configures these executable values at runtime.
RULE_TRACEABILITY = {
    "GOODS_ABSOLUTE_VARIANCE": THREE_WAY_TOLERANCES,
    "GOODS_PERCENT_VARIANCE": THREE_WAY_TOLERANCES,
    "SERVICE_ABSOLUTE_VARIANCE": THREE_WAY_TOLERANCES,
    "SERVICE_PERCENT_VARIANCE": THREE_WAY_TOLERANCES,
    "PROBABLE_DUPLICATE_DAYS": DUPLICATE_DETECTION,
    "PROBABLE_DUPLICATE_AMOUNT_PERCENT": DUPLICATE_DETECTION,
    "NEW_VENDOR_DAYS": AUTHORITY_HIGH_RISK,
    "FRAUD_ESCALATION_INDICATOR_COUNT": FRAUD_INDICATORS,
    "AUTHORITY_BANDS": AUTHORITY_LIMITS,
}
