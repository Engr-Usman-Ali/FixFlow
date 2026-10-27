// Sidebar menu. Each item lists the permissions that unlock it (any one is enough).
import {
  Bell, Building2, ClipboardList, FilePlus2, Inbox, LayoutDashboard, LineChart, ScrollText, ShieldCheck,
  UserCircle, Users, Wrench,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { Permission } from "../types";

export interface NavItem {
  label: string | ((can: (p: Permission) => boolean) => string);
  to: string;
  icon: LucideIcon;
  anyOf?: Permission[];
  end?: boolean;
  group: "work" | "admin" | "me";
}

export const VIEW_REQUESTS: Permission[] = ["request.view_own", "request.view_assigned", "request.view_all"];

/** The request list is named after what the user can see in it. */
export const requestsLabel = (can: (p: Permission) => boolean) =>
  can("request.view_all") ? "All requests" : can("request.view_assigned") ? "My tasks" : "My requests";

export const NAV_ITEMS: NavItem[] = [
  { label: "Overview", to: "/app", icon: LayoutDashboard, end: true, group: "work" },
  { label: "Report a problem", to: "/app/requests/new", icon: FilePlus2, anyOf: ["request.create"], group: "work" },
  { label: "Review queue", to: "/app/queue", icon: Inbox, anyOf: ["request.review"], group: "work" },
  { label: requestsLabel, to: "/app/requests", icon: ClipboardList, anyOf: VIEW_REQUESTS, end: true, group: "work" },
  { label: "Equipment", to: "/app/equipment", icon: Wrench, anyOf: ["equipment.manage"], group: "work" },
  { label: "Reports", to: "/app/reports", icon: LineChart, anyOf: ["report.view"], group: "work" },
  { label: "Users", to: "/app/users", icon: Users, anyOf: ["user.manage"], group: "admin" },
  { label: "Roles & permissions", to: "/app/roles", icon: ShieldCheck, anyOf: ["user.manage"], group: "admin" },
  { label: "Company settings", to: "/app/settings", icon: Building2, anyOf: ["settings.manage"], group: "admin" },
  { label: "Audit log", to: "/app/audit", icon: ScrollText, anyOf: ["audit.view"], group: "admin" },
  { label: "Notifications", to: "/app/notifications", icon: Bell, group: "me" },
  { label: "My profile", to: "/app/profile", icon: UserCircle, group: "me" },
];

export const GROUP_TITLES: Record<NavItem["group"], string> = {
  work: "Workspace",
  admin: "Administration",
  me: "Account",
};
