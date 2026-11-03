from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.core.access_context import AccessPrincipalKind
from app.routers.irpf import _access_context


def test_router_builds_user_scoped_irpf_context() -> None:
    access = _access_context(7, SimpleNamespace(id=3))

    assert access.principal_kind is AccessPrincipalKind.USER
    assert access.user_id == 3
    assert access.portfolio_id == 7
    assert access.permissions == frozenset({"read:portfolio_irpf"})


def test_router_hides_nonpositive_portfolio_ids() -> None:
    with pytest.raises(HTTPException) as exc_info:
        _access_context(0, SimpleNamespace(id=3))

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Carteira nao encontrada."
