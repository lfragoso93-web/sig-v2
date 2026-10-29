from typing import Optional
from pydantic import BaseModel, EmailStr, field_validator
from app.schemas.password_policy import validate_strong_password


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    message: str
    reset_token: Optional[str] = None


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return validate_strong_password(v)


class TokenResponse(BaseModel):
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    mfa_required: bool = False
    mfa_token: Optional[str] = None


class MessageResponse(BaseModel):
    message: str


class GoogleOAuthUrlResponse(BaseModel):
    url: str
    enabled: bool


class GoogleCallbackRequest(BaseModel):
    code: str
    state: str


class MfaSetupResponse(BaseModel):
    secret: str
    uri: str
    qr_code: Optional[str] = None
    backup_codes: list[str]


class MfaEnableRequest(BaseModel):
    secret: str
    code: str
    backup_codes: list[str]


class MfaDisableRequest(BaseModel):
    code: str


class MfaVerifyRequest(BaseModel):
    mfa_token: str
    code: str


class MfaStatusResponse(BaseModel):
    mfa_enabled: bool
    auth_provider: str
    mfa_recommended: bool = False
