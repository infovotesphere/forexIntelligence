from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class RegisterRequest(BaseModel):
    email: EmailStr
    display_name: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=12, max_length=128)

    @field_validator("display_name")
    @classmethod
    def trim_display_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Display name cannot be blank")
        return normalized


class ProfileUpdateRequest(BaseModel):
    email: EmailStr | None = None
    display_name: str | None = Field(default=None, min_length=1, max_length=100)

    @field_validator("display_name")
    @classmethod
    def trim_display_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("Display name cannot be blank")
        return normalized

    @model_validator(mode="after")
    def require_profile_field(self) -> "ProfileUpdateRequest":
        if not self.model_fields_set:
            raise ValueError("Provide an email or display name to update")
        return self


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=12, max_length=128)


class UserProfile(BaseModel):
    email: EmailStr
    display_name: str | None
    role: str


class ManagedUser(UserProfile):
    id: str
    is_active: bool
    created_at: datetime


class AdminCreateUserRequest(BaseModel):
    email: EmailStr
    display_name: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=12, max_length=128)
    role: Literal["administrator", "viewer"] = "viewer"

    @field_validator("display_name")
    @classmethod
    def trim_display_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Display name cannot be blank")
        return normalized


class ManagedUserUpdateRequest(BaseModel):
    role: Literal["administrator", "viewer"] | None = None
    is_active: bool | None = None
    email: EmailStr | None = None
    display_name: str | None = Field(default=None, min_length=1, max_length=100)
    password: str | None = Field(default=None, min_length=12, max_length=128)

    @field_validator("display_name")
    @classmethod
    def trim_display_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("Display name cannot be blank")
        return normalized

    @model_validator(mode="after")
    def require_user_field(self) -> "ManagedUserUpdateRequest":
        if not self.model_fields_set:
            raise ValueError("Provide a user field to update")
        return self


class AuthenticatedUser(BaseModel):
    email: EmailStr
    role: str
