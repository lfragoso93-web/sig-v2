import pytest
from pydantic import ValidationError

from app.schemas.auth import ResetPasswordRequest
from app.schemas.password_policy import validate_strong_password
from app.schemas.user import AdminResetPasswordRequest, UserCreate, UserPasswordUpdate


@pytest.mark.parametrize(
    "password, message",
    [
        ("Aa1!aaaaa", "minimo 10"),
        ("aa1!aaaaaa", "maiuscula"),
        ("AA1!AAAAAA", "minuscula"),
        ("Aa!!aaaaaa", "numero"),
        ("Aa11aaaaaa", "caractere especial"),
    ],
)
def test_password_policy_rejects_weak_passwords(password: str, message: str):
    with pytest.raises(ValueError, match=message):
        validate_strong_password(password)


def test_password_policy_accepts_canonical_boundary():
    assert validate_strong_password("Aa1!aaaaaa") == "Aa1!aaaaaa"


@pytest.mark.parametrize(
    "schema,payload",
    [
        (UserCreate, {"name": "User", "email": "user@example.com", "password": "Aa1!aaaaa"}),
        (UserPasswordUpdate, {"current_password": "old-password", "new_password": "Aa1!aaaaa"}),
        (AdminResetPasswordRequest, {"new_password": "Aa1!aaaaa"}),
        (ResetPasswordRequest, {"token": "token", "new_password": "Aa1!aaaaa"}),
    ],
)
def test_password_schemas_share_strong_policy(schema, payload):
    with pytest.raises(ValidationError):
        schema(**payload)


@pytest.mark.parametrize(
    "schema,payload",
    [
        (UserCreate, {"name": "User", "email": "user@example.com", "password": "Aa1!aaaaaa"}),
        (UserPasswordUpdate, {"current_password": "old-password", "new_password": "Aa1!aaaaaa"}),
        (AdminResetPasswordRequest, {"new_password": "Aa1!aaaaaa"}),
        (ResetPasswordRequest, {"token": "token", "new_password": "Aa1!aaaaaa"}),
    ],
)
def test_password_schemas_accept_canonical_boundary(schema, payload):
    assert schema(**payload)
