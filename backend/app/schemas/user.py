from pydantic import BaseModel, EmailStr, field_validator
from app.schemas.password_policy import validate_strong_password
from app.models.user import UserRole
from datetime import datetime
from typing import Optional


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return validate_strong_password(v)


class UserUpdate(BaseModel):
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    onboarding_completed: Optional[bool] = None


class UserPasswordUpdate(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return validate_strong_password(v)


class UserAdminUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class UserRoleUpdate(BaseModel):
    role: UserRole


class AdminResetPasswordRequest(BaseModel):
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return validate_strong_password(v)


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    role: UserRole
    is_active: bool
    avatar_url: Optional[str] = None
    onboarding_completed: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    id: int
    name: str
    email: str
    role: UserRole
    is_active: bool
    avatar_url: Optional[str] = None
    onboarding_completed: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
