from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from enum import Enum


class OnboardingStatus(str, Enum):
    PENDING_VERIFICATION = "pending_verification"
    VERIFIED = "verified"


class UserBase(BaseModel):
    email: EmailStr = Field(..., title="user email address")

class UserCreate(UserBase):
    password: str = Field(..., title="user password")

    class Config:
        from_attributes = True


class OTPData(BaseModel):
    email: str
    code: Optional[str] = None

    class Config:
        from_attributes = True


class OneTimePassword(BaseModel):
    code: str


class TokenData(BaseModel):
    email: Optional[str] = None


class ForgetPassword(BaseModel):
    email: str

class ResetPassword(BaseModel):
    token: str
    password: str

    class Config:
        from_attributes = True
