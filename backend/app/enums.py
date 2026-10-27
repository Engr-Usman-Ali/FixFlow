"""Controlled value lists (SRS DR-006).

Statuses, priorities and conditions are fixed by the SRS workflow, so they are
stored as checked text values. Categories and locations differ per company, so
they live in their own tables (see models.py).
"""
from enum import Enum


class Role(str, Enum):
    EMPLOYEE = "Employee"
    TECHNICIAN = "Technician"
    MANAGER = "Manager"
    ADMIN = "System Administrator"


class Status(str, Enum):
    NEW = "New"
    UNDER_REVIEW = "Under Review"
    ASSIGNED = "Assigned"
    IN_PROGRESS = "In Progress"
    ON_HOLD = "On Hold"
    RESOLVED = "Resolved"
    CLOSED = "Closed"
    REJECTED = "Rejected"


class Priority(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class Condition(str, Enum):
    GOOD = "Good"
    FAIR = "Fair"
    POOR = "Poor"
    OUT_OF_SERVICE = "Out of Service"


class Permission(str, Enum):
    """Fine-grained actions. Endpoints check permissions, never role names."""

    REQUEST_CREATE = "request.create"
    REQUEST_VIEW_OWN = "request.view_own"
    REQUEST_VIEW_ASSIGNED = "request.view_assigned"
    REQUEST_VIEW_ALL = "request.view_all"
    REQUEST_COMMENT = "request.comment"
    REQUEST_REVIEW = "request.review"
    REQUEST_ASSIGN = "request.assign"
    REQUEST_WORK = "request.work"
    REQUEST_WORK_ANY = "request.work_any"
    REQUEST_CLOSE = "request.close"
    EQUIPMENT_VIEW = "equipment.view"
    EQUIPMENT_MANAGE = "equipment.manage"
    REPORT_VIEW = "report.view"
    AI_SUGGEST = "ai.suggest"
    USER_MANAGE = "user.manage"
    SETTINGS_MANAGE = "settings.manage"
    AUDIT_VIEW = "audit.view"
