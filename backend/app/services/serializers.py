"""Turn database rows into API responses, adding values that are derived, not stored."""
from typing import Mapping

from ..deps import permissions_of
from ..enums import Permission as P
from ..enums import Priority
from ..models import MaintenanceRequest, User
from ..schemas import RequestDetail, RequestOut
from ..workflow import ASSIGNABLE_STATES, FINISHED_STATES, WORK_LOG_STATES, allowed_targets, due_at, is_overdue


def _with_due(out: RequestOut, req: MaintenanceRequest, sla: Mapping[Priority, int]) -> RequestOut:
    out.due_at = due_at(req.created_at, req.priority, sla)
    out.overdue = is_overdue(req.status, req.created_at, req.priority, sla)
    return out


def request_out(req: MaintenanceRequest, sla: Mapping[Priority, int]) -> RequestOut:
    return _with_due(RequestOut.model_validate(req), req, sla)


def request_detail(req: MaintenanceRequest, user: User, sla: Mapping[Priority, int]) -> RequestDetail:
    detail = RequestDetail.model_validate(req)
    _with_due(detail, req, sla)
    perms = permissions_of(user)
    is_assignee = req.technician_id == user.id

    detail.allowed_transitions = allowed_targets(req.status, perms, is_assignee)
    detail.can_assign = P.REQUEST_ASSIGN in perms and req.status in ASSIGNABLE_STATES
    detail.can_set_priority = P.REQUEST_REVIEW in perms and req.status not in FINISHED_STATES
    detail.can_add_work_log = (
        req.status in WORK_LOG_STATES
        and P.REQUEST_WORK in perms
        and (is_assignee or P.REQUEST_WORK_ANY in perms)
    )
    detail.can_comment = P.REQUEST_COMMENT in perms
    return detail
