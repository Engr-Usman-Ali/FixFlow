// Shared TypeScript types that mirror the API responses.

export const ROLES = ["Employee", "Technician", "Manager", "System Administrator"] as const;
export const STATUSES = ["New", "Under Review", "Assigned", "In Progress", "On Hold", "Resolved", "Closed", "Rejected"] as const;
export const PRIORITIES = ["Low", "Medium", "High", "Critical"] as const;
export const CONDITIONS = ["Good", "Fair", "Poor", "Out of Service"] as const;

export type Role = (typeof ROLES)[number];
export type Status = (typeof STATUSES)[number];
export type Priority = (typeof PRIORITIES)[number];
export type Condition = (typeof CONDITIONS)[number];

export type Permission =
  | "request.create" | "request.view_own" | "request.view_assigned" | "request.view_all"
  | "request.comment" | "request.review" | "request.assign" | "request.work" | "request.work_any"
  | "request.close" | "equipment.view" | "equipment.manage" | "report.view" | "ai.suggest"
  | "user.manage" | "settings.manage" | "audit.view";

// ---- Company -------------------------------------------------------------
export interface OrganizationBrief { id: number; name: string; request_prefix: string }
export interface OrganizationSettings extends OrganizationBrief {
  join_code: string; allow_self_signup: boolean; ai_enabled: boolean; ai_configured: boolean; ai_model: string | null;
}
export interface LookupBrief { id: number; name: string }
export interface Lookup extends LookupBrief { is_active: boolean }
export interface SlaItem { priority: Priority; target_hours: number }

// ---- People --------------------------------------------------------------
export interface UserBrief { id: number; name: string; role: Role }
export interface User extends UserBrief {
  email: string; is_active: boolean; is_locked: boolean; last_login_at: string | null; created_at: string;
}
export interface SessionUser extends User { organization: OrganizationBrief; permissions: Permission[] }
export interface TokenResponse { access_token: string; expires_at: string; user: SessionUser }
export interface RoleInfo { name: Role; description: string; permissions: Permission[]; user_count: number }
export interface PermissionInfo { code: Permission; description: string }

// ---- Equipment -----------------------------------------------------------
export interface EquipmentBrief { id: number; asset_code: string; name: string }
export interface Equipment extends EquipmentBrief {
  category: LookupBrief; location: LookupBrief; condition: Condition; description: string | null;
  is_active: boolean; request_count: number;
}
export interface EquipmentInput {
  asset_code: string; name: string; category_id: number | ""; location_id: number | "";
  condition: Condition; description: string; is_active: boolean;
}

// ---- Requests ------------------------------------------------------------
export interface MaintenanceRequest {
  id: number; ref: string; request_number: number; title: string; description: string;
  category: LookupBrief; location: LookupBrief; location_detail: string | null;
  priority: Priority; priority_confirmed: boolean; status: Status;
  creator: UserBrief; technician: UserBrief | null; equipment: EquipmentBrief | null;
  due_at: string | null; overdue: boolean; completion_details: string | null;
  resolved_at: string | null; closed_at: string | null; closed_by: UserBrief | null;
  created_at: string; updated_at: string;
}
export interface WorkLog {
  id: number; author: UserBrief; diagnosis: string | null; action_taken: string | null;
  materials_used: string | null; created_at: string;
}
export interface CommentItem { id: number; author: UserBrief; body: string; created_at: string }
export interface StatusHistoryItem {
  id: number; old_status: Status | null; new_status: Status; changed_by: UserBrief; reason: string | null; changed_at: string;
}
export interface AuditItem { id: number; actor: UserBrief; action: string; detail: string; created_at: string }
export interface AssignmentItem {
  id: number; technician: UserBrief; assigned_by: UserBrief; assigned_at: string; ended_at: string | null; reason: string | null;
}
export interface RequestDetail extends MaintenanceRequest {
  work_logs: WorkLog[]; comments: CommentItem[]; history: StatusHistoryItem[]; audit: AuditItem[];
  assignments: AssignmentItem[]; allowed_transitions: Status[];
  can_assign: boolean; can_set_priority: boolean; can_add_work_log: boolean; can_comment: boolean;
}
export interface RequestInput {
  title: string; description: string; category_id: number; location_id: number; location_detail?: string;
  priority: Priority; equipment_id: number | null; ai_suggestion_used: boolean;
}
export interface RequestFilters {
  q: string; status: string[]; category_id: string; priority: string; location_id: string;
  technician_id: string; overdue: boolean; date_from: string; date_to: string;
  sort: string; order: "asc" | "desc"; page: number;
}

// ---- Misc ----------------------------------------------------------------
export interface Page<T> { items: T[]; total: number; page: number; page_size: number }
export interface NotificationItem {
  id: number; request_id: number | null; event_type: string; message: string; read_at: string | null; created_at: string;
}
export interface AiSuggestion { category_id: number; category: string; priority: Priority; rationale: string; model: string }
export interface AuditEvent {
  id: number; action: string; detail: string; created_at: string; actor: UserBrief;
  target_user: UserBrief | null; request_id: number | null; request_ref: string | null;
}

export interface Overview {
  total: number; open: number; overdue: number; awaiting_review: number; awaiting_closure: number;
  by_status: Record<string, number>; recent: MaintenanceRequest[];
}
export interface AdminOverview {
  users_total: number; users_active: number; users_locked: number; by_role: Record<string, number>;
  categories_active: number; locations_active: number; equipment_total: number;
  requests_total: number; requests_open: number;
  recent_audit: { id: number; action: string; detail: string; created_at: string; actor: string }[];
}
export interface Summary {
  total: number; pending: number; in_progress: number; resolved: number; rejected: number; overdue: number;
  avg_completion_hours: number | null;
  by_status: Record<string, number>; by_category: Record<string, number>;
  by_priority: Record<string, number>; by_location: Record<string, number>;
  technician_workload: { technician_id: number; technician: string; open: number; completed: number; avg_hours: number | null }[];
  repeated_equipment: { equipment_id: number; asset_code: string; name: string; requests: number }[];
  sla_hours: Record<string, number>;
}
