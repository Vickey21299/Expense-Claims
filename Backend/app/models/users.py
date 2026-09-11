"""
app/models/users.py
Pydantic schemas for users.
"""
from __future__ import annotations
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, field_validator

from app.models.enums import UserRole


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------
class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    department: str | None = None
    role: UserRole = UserRole.STAFF
    job_title: str | None = None


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------
class UserCreate(UserBase):
    external_id: str | None = None
    manager_id: UUID | None = None


class UserUpdate(BaseModel):
    full_name: str | None = None
    department: str | None = None
    role: UserRole | None = None
    job_title: str | None = None
    manager_id: UUID | None = None
    is_active: bool | None = None


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------
class UserOut(UserBase):
    id: UUID
    external_id: str | None = None
    manager_id: UUID | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserListOut(BaseModel):
    total: int
    users: list[UserOut]
