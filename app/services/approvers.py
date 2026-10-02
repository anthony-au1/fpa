import json
from pathlib import Path

from pydantic import TypeAdapter

from app.domain.finance import ApprovalRole
from app.domain.models import ApprovalDecision
from app.domain.workflow import ApprovalContext, ApproverRecord


class ApproverDenied(PermissionError):
    pass


ROLE_RANK = {
    ApprovalRole.COST_CENTRE_MANAGER.value: 1,
    ApprovalRole.DEPARTMENT_DIRECTOR.value: 2,
    ApprovalRole.EXECUTIVE_DIRECTOR.value: 3,
    ApprovalRole.CHIEF_FINANCIAL_OFFICER.value: 4,
    ApprovalRole.CHIEF_EXECUTIVE_OFFICER.value: 5,
}


class FixtureApproverDirectory:
    """Simulated identity/authority directory; not enterprise authentication."""

    def __init__(self, fixture_file: Path) -> None:
        records = TypeAdapter(list[ApproverRecord]).validate_python(
            json.loads(fixture_file.read_text())
        )
        self._records = {record.approver_id: record for record in records}

    def validate(self, decision: ApprovalDecision, context: ApprovalContext) -> ApproverRecord:
        record = self._records.get(decision.approver_id)
        if record is None or not record.active:
            raise ApproverDenied("Approver is not active in the simulated directory")
        if decision.approver_role not in record.roles:
            raise ApproverDenied("Claimed approver role does not match simulated directory")
        if context.currency != "AUD":
            raise ApproverDenied("Simulated directory validates AUD authority only")
        if record.maximum_approval_aud is None or record.maximum_approval_aud < context.amount:
            raise ApproverDenied("Approver has insufficient simulated monetary authority")
        monetary_roles = [role for role in context.required_approval_roles if role in ROLE_RANK]
        if monetary_roles and ROLE_RANK.get(decision.approver_role, 0) < min(
            ROLE_RANK[role] for role in monetary_roles
        ):
            raise ApproverDenied("Approver role is below the required authority level")
        return record
