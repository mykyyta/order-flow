from apps.production.domain.status import STATUS_FINISHED as LEGACY_STATUS_FINISHED
from apps.production.domain.status import STATUS_FINISHED, validate_status
from apps.production.domain.transitions import get_allowed_transitions


def test_production_domain_reuses_order_status_policies():
    assert STATUS_FINISHED == LEGACY_STATUS_FINISHED
    assert validate_status(" DOING ") == "doing"
    assert STATUS_FINISHED in get_allowed_transitions("doing")
