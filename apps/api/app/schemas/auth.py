from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class AuthenticatedUser(BaseModel):
    email: EmailStr
    role: str
