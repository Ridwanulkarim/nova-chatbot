import re
from typing import Optional
from pydantic import BaseModel, Field, field_validator

EMAIL_REGEX = re.compile(r"^[\w\.-]+@[\w\.-]+\.\w+$")

class UserRegister(BaseModel):
    email: str
    password: str = Field(..., min_length=6)
    full_name: Optional[str] = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        clean = v.strip().lower()
        if not EMAIL_REGEX.match(clean):
            raise ValueError("Invalid email format")
        return clean

class UserLogin(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    full_name: Optional[str] = None

class UserOut(BaseModel):
    id: str
    email: str
    full_name: Optional[str] = None
    is_active: bool
    created_at: str

    class Config:
        from_attributes = True
