"""Database tables (SRS section 6.1), normalised to third normal form.

1NF  Every column holds one atomic value; no lists or repeating groups
     (materials, comments, assignments and history are separate rows).
2NF  Every table has a single-column surrogate primary key, or (for the two
     link tables) every non-key column depends on the whole composite key.
3NF  No non-key column depends on another non-key column:
     * role names, permission codes, categories, locations and service
       targets are stored once in their own tables and referenced by id;
     * child rows (assignments, work logs, comments, history, notifications)
       do not repeat the company; it is reached through their parent;
     * values that can be calculated (request reference, due date, overdue
       flag) are derived in code, not stored.
     Where a table keeps ``organization_id`` next to another company-scoped
     foreign key (equipment, requests, categories, locations), the column is
     part of a candidate key such as (organization_id, asset_code), so it is a
     prime attribute and the table stays in 3NF.

Multi-company: every company (organization) sees only its own rows. The API
always filters by the signed-in user's organization_id.
"""
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base
from .enums import Condition, Priority, Role, Status


def utcnow() -> datetime:
    """All timestamps are stored in UTC (DR-005)."""
    return datetime.now(timezone.utc)


def enum_col(enum_cls, name: str, length: int = 30):
    """Store a controlled value as text with a CHECK constraint (DR-006)."""
    return SAEnum(
        enum_cls,
        name=name,
        native_enum=False,
        create_constraint=True,
        length=length,
        values_callable=lambda e: [i.value for i in e],
        validate_strings=True,
    )


Timestamp = DateTime(timezone=True)


# --------------------------------------------------------------- companies ---
class Organization(Base):
    """A company using FixFlow. Its settings are the 'system configuration'."""

    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    join_code: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    request_prefix: Mapped[str] = mapped_column(String(6))
    allow_self_signup: Mapped[bool] = mapped_column(Boolean, default=True)
    ai_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(Timestamp, default=utcnow)


class SlaPolicy(Base):
    """Service target per company and priority, used for the overdue rule (BR-010)."""

    __tablename__ = "sla_policies"
    __table_args__ = (CheckConstraint("target_hours > 0", name="positive_hours"),)

    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), primary_key=True)
    priority: Mapped[Priority] = mapped_column(enum_col(Priority, "sla_priority"), primary_key=True)
    target_hours: Mapped[int] = mapped_column(Integer)


# ------------------------------------------------------------------- RBAC ---
class RoleRecord(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[Role] = mapped_column(enum_col(Role, "role_name"), unique=True)
    description: Mapped[str] = mapped_column(String(255))

    permissions: Mapped[list["PermissionRecord"]] = relationship(
        secondary="role_permissions", order_by="PermissionRecord.code"
    )


class PermissionRecord(Base):
    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(60), unique=True)
    description: Mapped[str] = mapped_column(String(255))


class RolePermission(Base):
    __tablename__ = "role_permissions"

    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
    permission_id: Mapped[int] = mapped_column(ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True)


# ------------------------------------------------------------------ users ---
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"))
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)

    # Password = PBKDF2-HMAC-SHA256(password, per-user random salt [+ pepper]).
    password_hash: Mapped[str] = mapped_column(String(128))
    password_salt: Mapped[str] = mapped_column(String(64))
    password_iterations: Mapped[int] = mapped_column(Integer)
    password_changed_at: Mapped[datetime] = mapped_column(Timestamp, default=utcnow)

    # Raising token_version signs the user out everywhere (logout, role change, reset).
    token_version: Mapped[int] = mapped_column(Integer, default=0)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[Optional[datetime]] = mapped_column(Timestamp, nullable=True)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(Timestamp, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(Timestamp, default=utcnow)

    organization: Mapped["Organization"] = relationship()
    role_record: Mapped["RoleRecord"] = relationship()

    @property
    def role(self) -> Role:
        return self.role_record.name

    @property
    def is_locked(self) -> bool:
        if not self.locked_until:
            return False
        until = self.locked_until
        if until.tzinfo is None:  # SQLite (tests) drops the timezone
            until = until.replace(tzinfo=timezone.utc)
        return until > utcnow()


# -------------------------------------------------- company lookup tables ---
class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (UniqueConstraint("organization_id", "name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(80))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Location(Base):
    __tablename__ = "locations"
    __table_args__ = (UniqueConstraint("organization_id", "name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


# -------------------------------------------------------------- equipment ---
class Equipment(Base):
    __tablename__ = "equipment"
    # FR-054 / DR-004: asset codes are unique inside each company.
    __table_args__ = (UniqueConstraint("organization_id", "asset_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    asset_code: Mapped[str] = mapped_column(String(40))
    name: Mapped[str] = mapped_column(String(160))
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"))
    condition: Mapped[Condition] = mapped_column(enum_col(Condition, "equipment_condition"), default=Condition.GOOD)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(Timestamp, default=utcnow)

    category: Mapped["Category"] = relationship()
    location: Mapped["Location"] = relationship()


# --------------------------------------------------- maintenance requests ---
class MaintenanceRequest(Base):
    __tablename__ = "maintenance_requests"
    # DR-001: each company numbers its own requests 1, 2, 3...
    __table_args__ = (UniqueConstraint("organization_id", "request_number"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    request_number: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), index=True)
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"), index=True)
    location_detail: Mapped[Optional[str]] = mapped_column(String(160), nullable=True)
    priority: Mapped[Priority] = mapped_column(enum_col(Priority, "request_priority"), default=Priority.MEDIUM)
    priority_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[Status] = mapped_column(enum_col(Status, "request_status"), default=Status.NEW, index=True)

    creator_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    technician_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), index=True, nullable=True)
    equipment_id: Mapped[Optional[int]] = mapped_column(ForeignKey("equipment.id"), index=True, nullable=True)
    closed_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)

    completion_details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(Timestamp, nullable=True)
    closed_at: Mapped[Optional[datetime]] = mapped_column(Timestamp, nullable=True)
    created_at: Mapped[datetime] = mapped_column(Timestamp, default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(Timestamp, default=utcnow, onupdate=utcnow)

    organization: Mapped["Organization"] = relationship()
    category: Mapped["Category"] = relationship()
    location: Mapped["Location"] = relationship()
    creator: Mapped["User"] = relationship(foreign_keys=[creator_id])
    technician: Mapped[Optional["User"]] = relationship(foreign_keys=[technician_id])
    closed_by: Mapped[Optional["User"]] = relationship(foreign_keys=[closed_by_id])
    equipment: Mapped[Optional["Equipment"]] = relationship()

    assignments: Mapped[list["Assignment"]] = relationship(
        back_populates="request", order_by="Assignment.assigned_at", cascade="all, delete-orphan"
    )
    work_logs: Mapped[list["WorkLog"]] = relationship(
        back_populates="request", order_by="WorkLog.created_at", cascade="all, delete-orphan"
    )
    comments: Mapped[list["Comment"]] = relationship(
        back_populates="request", order_by="Comment.created_at", cascade="all, delete-orphan"
    )
    history: Mapped[list["StatusHistory"]] = relationship(
        back_populates="request", order_by="StatusHistory.changed_at", cascade="all, delete-orphan"
    )
    audit: Mapped[list["AuditEvent"]] = relationship(
        back_populates="request", order_by="AuditEvent.created_at", cascade="all, delete-orphan"
    )

    @property
    def ref(self) -> str:
        """Human-friendly id such as ACME-00042 (derived, never stored)."""
        return f"{self.organization.request_prefix}-{self.request_number:05d}"


class Assignment(Base):
    """Current and past technician assignments (FR-023)."""

    __tablename__ = "assignments"

    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("maintenance_requests.id", ondelete="CASCADE"), index=True)
    technician_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    assigned_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    assigned_at: Mapped[datetime] = mapped_column(Timestamp, default=utcnow)
    ended_at: Mapped[Optional[datetime]] = mapped_column(Timestamp, nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    request: Mapped["MaintenanceRequest"] = relationship(back_populates="assignments")
    technician: Mapped["User"] = relationship(foreign_keys=[technician_id])
    assigned_by: Mapped["User"] = relationship(foreign_keys=[assigned_by_id])


class WorkLog(Base):
    """Append-only inspection and repair entries (FR-031, FR-032, FR-035)."""

    __tablename__ = "work_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("maintenance_requests.id", ondelete="CASCADE"), index=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    diagnosis: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    action_taken: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    materials_used: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(Timestamp, default=utcnow)

    request: Mapped["MaintenanceRequest"] = relationship(back_populates="work_logs")
    author: Mapped["User"] = relationship()


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("maintenance_requests.id", ondelete="CASCADE"), index=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(Timestamp, default=utcnow)

    request: Mapped["MaintenanceRequest"] = relationship(back_populates="comments")
    author: Mapped["User"] = relationship()


class StatusHistory(Base):
    """Every status change is appended here; rows are never edited (FR-035)."""

    __tablename__ = "status_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("maintenance_requests.id", ondelete="CASCADE"), index=True)
    old_status: Mapped[Optional[Status]] = mapped_column(enum_col(Status, "history_old_status"), nullable=True)
    new_status: Mapped[Status] = mapped_column(enum_col(Status, "history_new_status"))
    changed_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    changed_at: Mapped[datetime] = mapped_column(Timestamp, default=utcnow)

    request: Mapped["MaintenanceRequest"] = relationship(back_populates="history")
    changed_by: Mapped["User"] = relationship()


class Notification(Base):
    """In-app notification; only its recipient can read it (BR-009)."""

    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    recipient_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    request_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("maintenance_requests.id", ondelete="CASCADE"), nullable=True
    )
    event_type: Mapped[str] = mapped_column(String(40))
    message: Mapped[str] = mapped_column(String(300))
    read_at: Mapped[Optional[datetime]] = mapped_column(Timestamp, nullable=True)
    created_at: Mapped[datetime] = mapped_column(Timestamp, default=utcnow, index=True)


class AuditEvent(Base):
    """Who did what and when (FR-100, FR-101).

    Request events (priority, assignment) carry request_id; administration
    events (user created, role changed, settings updated) carry target_user_id
    or neither. The company is reached through the acting user.
    """

    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    request_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("maintenance_requests.id", ondelete="CASCADE"), index=True, nullable=True
    )
    target_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(40), index=True)
    detail: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(Timestamp, default=utcnow, index=True)

    request: Mapped[Optional["MaintenanceRequest"]] = relationship(back_populates="audit")
    actor: Mapped["User"] = relationship(foreign_keys=[actor_id])
    target_user: Mapped[Optional["User"]] = relationship(foreign_keys=[target_user_id])
