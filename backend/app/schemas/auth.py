from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MessageResponse(BaseModel):
    message: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    message: str
    # reset_token e reset_url sao retornados apenas para ambientes sem SMTP
    # Em producao com SMTP configurado, remover esses campos e enviar por e-mail
    reset_token: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str
