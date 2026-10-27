// One function per API endpoint, so pages never build URLs by hand.
import { http } from "./client";
import type {
  AdminOverview, AiSuggestion, AuditEvent, Equipment, EquipmentInput, Lookup, MaintenanceRequest,
  NotificationItem, OrganizationSettings, Overview, Page, PermissionInfo, Priority, RequestDetail,
  RequestFilters, RequestInput, Role, RoleInfo, SessionUser, SlaItem, Status, Summary, TokenResponse, User, UserBrief,
} from "../types";

export const authApi = {
  login: (email: string, password: string) => http.post<TokenResponse>("/auth/login", { email, password }),
  registerCompany: (data: {
    organization_name: string; request_prefix?: string; name: string; email: string; password: string;
  }) => http.post<TokenResponse>("/auth/register-organization", data),
  join: (data: { join_code: string; name: string; email: string; password: string }) =>
    http.post<TokenResponse>("/auth/join", data),
  me: () => http.get<SessionUser>("/auth/me"),
  logout: () => http.post("/auth/logout"),
  updateProfile: (name: string) => http.patch<SessionUser>("/auth/me", { name }),
  changePassword: (current_password: string, new_password: string) =>
    http.post<TokenResponse>("/auth/change-password", { current_password, new_password }),
};

type ListParams = Partial<RequestFilters> & { page_size?: number; equipment_id?: number; unassigned?: boolean };

export const requestApi = {
  list: (f: ListParams) => http.get<Page<MaintenanceRequest>>("/requests", { page_size: 10, ...f }),
  get: (id: number | string) => http.get<RequestDetail>(`/requests/${id}`),
  create: (data: RequestInput) => http.post<MaintenanceRequest>("/requests", data),
  setPriority: (id: number, priority: Priority) => http.post<RequestDetail>(`/requests/${id}/priority`, { priority }),
  assign: (id: number, data: { technician_id: number; priority?: Priority; note?: string }) =>
    http.post<RequestDetail>(`/requests/${id}/assign`, data),
  changeStatus: (id: number, data: { status: Status; reason?: string; completion_details?: string }) =>
    http.post<RequestDetail>(`/requests/${id}/status`, data),
  addWorkLog: (id: number, data: { diagnosis?: string; action_taken?: string; materials_used?: string }) =>
    http.post(`/requests/${id}/work-logs`, data),
  addComment: (id: number, body: string) => http.post(`/requests/${id}/comments`, { body }),
};

export const equipmentApi = {
  list: (params?: { q?: string; active_only?: boolean }) => http.get<Equipment[]>("/equipment", params),
  create: (data: EquipmentInput) => http.post<Equipment>("/equipment", data),
  update: (id: number, data: EquipmentInput) => http.put<Equipment>(`/equipment/${id}`, data),
  history: (id: number) => http.get<MaintenanceRequest[]>(`/equipment/${id}/history`),
};

export const userApi = {
  list: (params?: { q?: string; role?: Role | "" }) => http.get<User[]>("/users", params),
  technicians: () => http.get<UserBrief[]>("/users/technicians"),
  create: (data: { name: string; email: string; password: string; role: Role }) => http.post<User>("/users", data),
  update: (id: number, data: { name?: string; role?: Role; is_active?: boolean }) => http.patch<User>(`/users/${id}`, data),
  resetPassword: (id: number, new_password: string) => http.post<User>(`/users/${id}/reset-password`, { new_password }),
  unlock: (id: number) => http.post<User>(`/users/${id}/unlock`),
  roles: () => http.get<RoleInfo[]>("/roles"),
  permissions: () => http.get<PermissionInfo[]>("/roles/permissions"),
};

export const orgApi = {
  get: () => http.get<OrganizationSettings>("/organization"),
  update: (data: Partial<Pick<OrganizationSettings, "name" | "request_prefix" | "allow_self_signup" | "ai_enabled">>) =>
    http.patch<OrganizationSettings>("/organization", data),
  regenerateJoinCode: () => http.post<OrganizationSettings>("/organization/join-code"),
  categories: (includeInactive = false) => http.get<Lookup[]>("/organization/categories", { include_inactive: includeInactive }),
  createCategory: (name: string) => http.post<Lookup>("/organization/categories", { name }),
  updateCategory: (id: number, data: { name: string; is_active: boolean }) => http.put<Lookup>(`/organization/categories/${id}`, data),
  locations: (includeInactive = false) => http.get<Lookup[]>("/organization/locations", { include_inactive: includeInactive }),
  createLocation: (name: string) => http.post<Lookup>("/organization/locations", { name }),
  updateLocation: (id: number, data: { name: string; is_active: boolean }) => http.put<Lookup>(`/organization/locations/${id}`, data),
  sla: () => http.get<SlaItem[]>("/organization/sla"),
  updateSla: (items: SlaItem[]) => http.put<SlaItem[]>("/organization/sla", { items }),
};

export const notificationApi = {
  list: (unreadOnly = false) => http.get<NotificationItem[]>("/notifications", { unread_only: unreadOnly }),
  unreadCount: () => http.get<{ count: number }>("/notifications/unread-count"),
  markRead: (id: number) => http.post(`/notifications/${id}/read`),
  markAllRead: () => http.post("/notifications/read-all"),
};

export const reportApi = {
  overview: () => http.get<Overview>("/reports/overview"),
  adminOverview: () => http.get<AdminOverview>("/reports/admin-overview"),
  summary: (dateFrom?: string, dateTo?: string) =>
    http.get<Summary>("/reports/summary", { date_from: dateFrom, date_to: dateTo }),
};

export const auditApi = {
  list: (params: { action?: string; date_from?: string; date_to?: string; page?: number }) =>
    http.get<Page<AuditEvent>>("/audit", { page_size: 25, ...params }),
};

export const aiApi = {
  status: () => http.get<{ enabled: boolean; model: string | null }>("/ai/status"),
  suggest: (title: string, description: string) => http.post<AiSuggestion>("/ai/suggest", { title, description }),
};
