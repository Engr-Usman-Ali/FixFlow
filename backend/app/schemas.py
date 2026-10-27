"""Request and response schemas. Input models validate on the server (DR-002, NFR-SEC-003)."""
from datetime import datetime
from typing import Generic, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .enums import Condition, Priority, Role, Status

EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
T = TypeVar("T")


class In(BaseModel):
    """Base for request bodies: trims spaces and rejects unknown fields."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class Out(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


def _email(v: str) -> str:
    return v.strip().lower()


# ------------------------------------------------------------ companies ---
class OrganizationBrief(Out):
    id: int
    name: str
    request_prefix: str


class OrganizationSettings(OrganizationBrief):
    join_code: str
    allow_self_signup: bool
    ai_enabled: bool
    ai_configured: bool = False  # true when GEMINI_API_KEY is set in .env
    ai_model: Optional[str] = None


class OrganizationUpdate(In):
    name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    request_prefix: Optional[str] = Field(default=None, pattern=r"^[A-Za-z]{2,6}$")
    allow_self_signup: Optional[bool] = None
    ai_enabled: Optional[bool] = None

    @field_validator("request_prefix")
    @classmethod
    def upper(cls, v: Optional[str]) -> Optional[str]:
        return v.upper() if v else v


class LookupBrief(Out):
    id: int
    name: str


class LookupOut(LookupBrief):
    is_active: bool


class LookupIn(In):
    name: str = Field(min_length=2, max_length=160)
    is_active: bool = True


class SlaItem(BaseModel):
    priority: Priority
    target_hours: int = Field(ge=1, le=24 * 365)


class SlaUpdate(In):
    items: list[SlaItem] = Field(min_length=1, max_length=4)


# ---------------------------------------------------------- users & auth ---
class UserBrief(Out):
    id: int
    name: str
    role: Role


class UserOut(UserBrief):
    email: str
    is_active: bool
    is_locked: bool
    last_login_at: Optional[datetime] = None
    created_at: datetime


class SessionUser(UserOut):
    organization: OrganizationBrief
    permissions: list[str] = []


class LoginIn(In):
    email: str = Field(pattern=EMAIL_PATTERN, max_length=255)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def normalise_email(cls, v: str) -> str:
        return _email(v)


class _NewAccount(In):
    name: str = Field(min_length=2, max_length=120)
    email: str = Field(pattern=EMAIL_PATTERN, max_length=255)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def normalise_email(cls, v: str) -> str:
        return _email(v)


class JoinIn(_NewAccount):
    """Employee sign-up into an existing company using its join code."""

    join_code: str = Field(min_length=4, max_length=16)

    @field_validator("join_code")
    @classmethod
    def upper(cls, v: str) -> str:
        return v.upper()


class RegisterOrganizationIn(_NewAccount):
    """Creates a new company and its first System Administrator."""

    organization_name: str = Field(min_length=2, max_length=120)
    request_prefix: Optional[str] = Field(default=None, pattern=r"^[A-Za-z]{2,6}$")


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    user: SessionUser


class ProfileUpdate(In):
    name: str = Field(min_length=2, max_length=120)


class PasswordChange(In):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class UserCreate(_NewAccount):
    role: Role = Role.EMPLOYEE


class UserUpdate(In):
    name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    role: Optional[Role] = None
    is_active: Optional[bool] = None


class PasswordReset(In):
    new_password: str = Field(min_length=8, max_length=128)


class PermissionOut(BaseModel):
    code: str
    description: str


class RoleOut(BaseModel):
    name: Role
    description: str
    permissions: list[str]
    user_count: int = 0


# -------------------------------------------------------------- equipment ---
class EquipmentBrief(Out):
    id: int
    asset_code: str
    name: str


class EquipmentIn(In):
    asset_code: str = Field(min_length=1, max_length=40, pattern=r"^[A-Za-z0-9._\-]+$")
    name: str = Field(min_length=2, max_length=160)
    category_id: int
    location_id: int
    condition: Condition = Condition.GOOD
    description: Optional[str] = Field(default=None, max_length=2000)
    is_active: bool = True

    @field_validator("asset_code")
    @classmethod
    def upper(cls, v: str) -> str:
        return v.upper()


class EquipmentOut(EquipmentBrief):
    category: LookupBrief
    location: LookupBrief
    condition: Condition
    description: Optional[str] = None
    is_active: bool
    request_count: int = 0


# --------------------------------------------------------------- requests ---
class RequestCreate(In):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=10, max_length=4000)
    category_id: int
    location_id: int
    location_detail: Optional[str] = Field(default=None, max_length=160)
    priority: Priority = Priority.MEDIUM
    equipment_id: Optional[int] = None
    ai_suggestion_used: bool = False


class RequestOut(Out):
    id: int
    ref: str
    request_number: int
    title: str
    description: str
    category: LookupBrief
    location: LookupBrief
    location_detail: Optional[str] = None
    priority: Priority
    priority_confirmed: bool
    status: Status
    creator: UserBrief
    technician: Optional[UserBrief] = None
    equipment: Optional[EquipmentBrief] = None
    due_at: Optional[datetime] = None  # filled from the company's service targets
    overdue: bool = False
    completion_details: Optional[str] = None
    resolved_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    closed_by: Optional[UserBrief] = None
    created_at: datetime
    updated_at: datetime


class WorkLogIn(In):
    diagnosis: Optional[str] = Field(default=None, max_length=3000)
    action_taken: Optional[str] = Field(default=None, max_length=3000)
    materials_used: Optional[str] = Field(default=None, max_length=1000)


class WorkLogOut(Out):
    id: int
    author: UserBrief
    diagnosis: Optional[str] = None
    action_taken: Optional[str] = None
    materials_used: Optional[str] = None
    created_at: datetime


class CommentIn(In):
    body: str = Field(min_length=1, max_length=2000)


class CommentOut(Out):
    id: int
    author: UserBrief
    body: str
    created_at: datetime


class StatusHistoryOut(Out):
    id: int
    old_status: Optional[Status] = None
    new_status: Status
    changed_by: UserBrief
    reason: Optional[str] = None
    changed_at: datetime


class RequestAuditOut(Out):
    id: int
    actor: UserBrief
    action: str
    detail: str
    created_at: datetime


class AssignmentOut(Out):
    id: int
    technician: UserBrief
    assigned_by: UserBrief
    assigned_at: datetime
    ended_at: Optional[datetime] = None
    reason: Optional[str] = None


class RequestDetail(RequestOut):
    work_logs: list[WorkLogOut] = []
    comments: list[CommentOut] = []
    history: list[StatusHistoryOut] = []
    audit: list[RequestAuditOut] = []
    assignments: list[AssignmentOut] = []
    # Worked out per viewer so the UI never has to guess permissions.
    allowed_transitions: list[Status] = []
    can_assign: bool = False
    can_set_priority: bool = False
    can_add_work_log: bool = False
    can_comment: bool = False


class AssignIn(In):
    technician_id: int
    priority: Optional[Priority] = None
    note: Optional[str] = Field(default=None, max_length=500)


class PriorityIn(In):
    priority: Priority


class StatusIn(In):
    status: Status
    reason: Optional[str] = Field(default=None, max_length=1000)
    completion_details: Optional[str] = Field(default=None, max_length=4000)


# ---------------------------------------------------- notifications/audit ---
class NotificationOut(Out):
    id: int
    request_id: Optional[int] = None
    event_type: str
    message: str
    read_at: Optional[datetime] = None
    created_at: datetime


class AuditEventOut(BaseModel):
    id: int
    action: str
    detail: str
    created_at: datetime
    actor: UserBrief
    target_user: Optional[UserBrief] = None
    request_id: Optional[int] = None
    request_ref: Optional[str] = None


# ------------------------------------------------------------------- AI ---
class SuggestIn(In):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=10, max_length=4000)


class SuggestOut(BaseModel):
    category_id: int
    category: str
    priority: Priority
    rationale: str
    model: str
