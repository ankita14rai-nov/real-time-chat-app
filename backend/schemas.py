from pydantic import BaseModel, EmailStr
from datetime import datetime

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    created_at: datetime
    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str

class FriendRequestCreate(BaseModel):
    receiver_email: EmailStr


class FriendResponse(BaseModel):
    id: int
    sender_id: int
    receiver_id: int
    status: str

    class Config:
        from_attributes = True


class FriendInfo(BaseModel):
    id: int
    username: str
    email: str

    class Config:
        from_attributes = True

# -----------------------------
# Message Schemas
# -----------------------------

class MessageCreate(BaseModel):
    receiver_email: EmailStr
    message: str


class MessageResponse(BaseModel):

    id: int

    sender_id: int

    receiver_id: int

    message: str | None = None

    file_name: str | None = None

    file_path: str | None = None

    message_type: str

    status: str

    created_at: datetime

    class Config:
        from_attributes = True


class MessageEdit(BaseModel):
    message: str


