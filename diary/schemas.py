from pydantic import BaseModel
from typing import Optional


class RegisterRequest(BaseModel):
    username: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class PostCreate(BaseModel):
    type: str
    content: Optional[str] = None
    media_url: Optional[str] = None
    segment: Optional[str] = None


class CommentCreate(BaseModel):
    content: str
    guest_name: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class ChangeUsernameRequest(BaseModel):
    new_username: str


class ChangeProfileRequest(BaseModel):
    url: Optional[str] = None
