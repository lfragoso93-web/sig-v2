from types import SimpleNamespace

import pytest
from app.models.user import UserRole
from app.routers.admin import require_superadmin, router
from app.schemas.corporate_event_review import CorporateEventReviewRequest
from fastapi import HTTPException
from pydantic import ValidationError


def test_review_endpoints_are_registered_under_admin_router():
    paths = {route.path for route in router.routes}

    assert "/corporate-events/review" in paths
    assert "/corporate-events/{event_id}/evidence" in paths
    assert "/corporate-events/{event_id}/projection-plan" in paths
    assert "/corporate-events/{event_id}/review" in paths


def test_corporate_review_remains_restricted_to_superadmin():
    with pytest.raises(HTTPException) as exc_info:
        require_superadmin(SimpleNamespace(role=UserRole.user))

    assert exc_info.value.status_code == 403


def test_review_requires_meaningful_justification():
    with pytest.raises(ValidationError):
        CorporateEventReviewRequest(decision="APPROVE", note="curta")
