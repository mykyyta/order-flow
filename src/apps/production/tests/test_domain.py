from apps.production.domain.status import STATUS_DONE, STATUS_IN_PROGRESS, validate_status
from apps.production.domain.transitions import get_allowed_transitions


def test_production_domain_status_validation():
    assert validate_status(" IN_PROGRESS ") == "in_progress"
    assert STATUS_DONE in get_allowed_transitions(STATUS_IN_PROGRESS)
