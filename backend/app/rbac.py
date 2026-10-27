"""Role-based access control (SRS 2.3, 7.1, NFR-SEC-001).

The matrix below is the single source of truth. On start-up it is written to
the ``roles``, ``permissions`` and ``role_permissions`` tables so the database
documents exactly what each role may do, and the API checks permissions with
``require_permission`` (deps.py) on every protected endpoint (FR-004).
"""
from .enums import Permission as P
from .enums import Role

ROLE_DESCRIPTIONS: dict[Role, str] = {
    Role.EMPLOYEE: "Reports problems and follows the progress of their own requests.",
    Role.TECHNICIAN: "Inspects assigned requests, records diagnosis and work, submits completion.",
    Role.MANAGER: "Reviews the queue, confirms priority, assigns technicians, keeps equipment, reads reports.",
    Role.ADMIN: "Maintains user access and company configuration. Not a maintenance workflow role.",
}

PERMISSION_DESCRIPTIONS: dict[P, str] = {
    P.REQUEST_CREATE: "Submit a maintenance request",
    P.REQUEST_VIEW_OWN: "View requests they submitted",
    P.REQUEST_VIEW_ASSIGNED: "View requests assigned to them",
    P.REQUEST_VIEW_ALL: "View every request in the company",
    P.REQUEST_COMMENT: "Comment on requests they can view",
    P.REQUEST_REVIEW: "Review, confirm priority, hold or reject requests",
    P.REQUEST_ASSIGN: "Assign and reassign technicians",
    P.REQUEST_WORK: "Record diagnosis, work logs and status on assigned requests",
    P.REQUEST_WORK_ANY: "Record work on any request, not only their own assignments",
    P.REQUEST_CLOSE: "Close, send back or reopen requests",
    P.EQUIPMENT_VIEW: "Read the equipment register",
    P.EQUIPMENT_MANAGE: "Create and update equipment records",
    P.REPORT_VIEW: "View management reports",
    P.AI_SUGGEST: "Ask the AI for category and priority suggestions",
    P.USER_MANAGE: "Create users, change roles, reset passwords, deactivate accounts",
    P.SETTINGS_MANAGE: "Change company settings, categories, locations and service targets",
    P.AUDIT_VIEW: "Read the company audit log",
}

ROLE_PERMISSIONS: dict[Role, frozenset[P]] = {
    Role.EMPLOYEE: frozenset({
        P.REQUEST_CREATE, P.REQUEST_VIEW_OWN, P.REQUEST_COMMENT, P.EQUIPMENT_VIEW, P.AI_SUGGEST,
    }),
    Role.TECHNICIAN: frozenset({
        P.REQUEST_VIEW_ASSIGNED, P.REQUEST_COMMENT, P.REQUEST_WORK, P.EQUIPMENT_VIEW,
    }),
    Role.MANAGER: frozenset({
        P.REQUEST_CREATE, P.REQUEST_VIEW_ALL, P.REQUEST_COMMENT, P.REQUEST_REVIEW, P.REQUEST_ASSIGN,
        P.REQUEST_WORK, P.REQUEST_WORK_ANY, P.REQUEST_CLOSE, P.EQUIPMENT_VIEW, P.EQUIPMENT_MANAGE,
        P.REPORT_VIEW, P.AI_SUGGEST,
    }),
    # Least privilege: administrators manage access and configuration but do not
    # read or change maintenance requests.
    Role.ADMIN: frozenset({P.USER_MANAGE, P.SETTINGS_MANAGE, P.AUDIT_VIEW}),
}


def permissions_for(role: Role) -> frozenset[P]:
    return ROLE_PERMISSIONS.get(role, frozenset())


def has_permission(role: Role, permission: P) -> bool:
    return permission in permissions_for(role)
