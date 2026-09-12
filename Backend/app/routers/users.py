"""
app/routers/users.py
CRUD endpoints for users.

GET  /api/v1/users                      List all users (filterable by role, active, email, external_id)
GET  /api/v1/users/{identifier}         Get user by UUID, external_id (e.g. usr-001), or email
POST /api/v1/users                      Create user
PUT  /api/v1/users/{identifier}         Update user by UUID, external_id, or email
GET  /api/v1/users/{identifier}/claims  List claims owned by this user (by UUID, external_id, or email)
"""
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.core.database import supabase
from app.core.logging import get_logger
from app.models.users import UserCreate, UserUpdate, UserOut, UserListOut
from app.models.claims import ClaimListOut
from app.models.enums import UserRole

router = APIRouter(prefix="/users", tags=["Users"])
logger = get_logger(__name__)


def _resolve_user_id(identifier: str) -> str | None:
    """Helper to find user UUID by UUID string, external_id, or email."""
    ident = identifier.strip()

    # 1. Try UUID validation
    try:
        val = UUID(ident)
        return str(val)
    except ValueError:
        pass

    # 2. Try email match
    if "@" in ident:
        res = supabase.table("users").select("id").ilike("email", ident).execute()
        if res.data and len(res.data) > 0:
            return res.data[0]["id"]
        return None

    # 3. Try external_id match
    res = supabase.table("users").select("id").eq("external_id", ident).execute()
    if res.data and len(res.data) > 0:
        return res.data[0]["id"]

    return None


@router.get("", response_model=UserListOut, summary="List all users")
def list_users(
    role: UserRole | None = Query(None, description="Filter by role"),
    is_active: bool | None = Query(None, description="Filter by active status"),
    email: str | None = Query(None, description="Filter by exact or partial email"),
    external_id: str | None = Query(None, description="Filter by external ID"),
):
    try:
        q = supabase.table("users").select("*")
        if role and hasattr(role, "value"):
            q = q.eq("role", role.value)
        elif role and isinstance(role, str):
            q = q.eq("role", role)
        if is_active is not None and isinstance(is_active, bool):
            q = q.eq("is_active", is_active)
        if email:
            q = q.ilike("email", f"%{email.strip()}%")
        if external_id:
            q = q.eq("external_id", external_id.strip())

        result = q.order("full_name").execute()
        logger.info("Listed users", extra={"count": len(result.data), "role_filter": role})
        return UserListOut(total=len(result.data), users=result.data)
    except Exception as exc:
        logger.error("Failed to list users", exc_info=exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{identifier}", response_model=UserOut, summary="Get user by UUID, external_id, or email")
def get_user(identifier: str):
    try:
        ident = identifier.strip()

        # Check if identifier is valid UUID
        is_uuid = False
        try:
            UUID(ident)
            is_uuid = True
        except ValueError:
            is_uuid = False

        if is_uuid:
            result = supabase.table("users").select("*").eq("id", ident).execute()
        elif "@" in ident:
            result = supabase.table("users").select("*").ilike("email", ident).execute()
        else:
            result = supabase.table("users").select("*").eq("external_id", ident).execute()

        if not result.data:
            raise HTTPException(status_code=404, detail=f"User '{identifier}' not found")

        return result.data[0]
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to get user", extra={"identifier": identifier}, exc_info=exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("", response_model=UserOut, status_code=201, summary="Create user")
def create_user(body: UserCreate):
    try:
        payload = body.model_dump(exclude_none=True)
        if "manager_id" in payload:
            payload["manager_id"] = str(payload["manager_id"])
        if "role" in payload:
            payload["role"] = payload["role"].value if hasattr(payload["role"], "value") else payload["role"]
        result = supabase.table("users").insert(payload).execute()
        logger.info("User created", extra={"email": body.email, "role": body.role})
        return result.data[0]
    except Exception as exc:
        logger.error("Failed to create user", exc_info=exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.put("/{identifier}", response_model=UserOut, summary="Update user by UUID, external_id, or email")
def update_user(identifier: str, body: UserUpdate):
    try:
        user_uuid = _resolve_user_id(identifier)
        if not user_uuid:
            raise HTTPException(status_code=404, detail=f"User '{identifier}' not found")

        payload = body.model_dump(exclude_none=True)
        if "manager_id" in payload:
            payload["manager_id"] = str(payload["manager_id"])
        if "role" in payload:
            payload["role"] = payload["role"].value if hasattr(payload["role"], "value") else payload["role"]
        result = supabase.table("users").update(payload).eq("id", user_uuid).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail=f"User '{identifier}' not found")
        logger.info("User updated", extra={"identifier": identifier, "user_uuid": user_uuid})
        return result.data[0]
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to update user", extra={"identifier": identifier}, exc_info=exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{identifier}/claims", response_model=ClaimListOut, summary="List claims by user (UUID, external_id, or email)")
def list_user_claims(
    identifier: str,
    status: str | None = Query(None, description="Filter by claim status"),
):
    try:
        user_uuid = _resolve_user_id(identifier)
        if not user_uuid:
            raise HTTPException(status_code=404, detail=f"User '{identifier}' not found")

        q = supabase.table("claims").select("*").eq("employee_id", user_uuid)
        if status:
            q = q.eq("status", status)
        result = q.order("created_at", desc=True).execute()
        logger.info(
            "Listed user claims",
            extra={"identifier": identifier, "user_uuid": user_uuid, "count": len(result.data)},
        )
        return ClaimListOut(total=len(result.data), claims=result.data)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to list user claims", extra={"identifier": identifier}, exc_info=exc)
        raise HTTPException(status_code=500, detail=str(exc))
