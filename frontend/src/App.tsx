import { Navigate, Route, Routes } from "react-router-dom";
import DashboardLayout from "./components/layout/DashboardLayout";
import ProtectedRoute from "./components/layout/ProtectedRoute";
import AuditLog from "./pages/admin/AuditLog";
import CompanySettings from "./pages/admin/CompanySettings";
import RolesPage from "./pages/admin/Roles";
import UsersPage from "./pages/admin/Users";
import Equipment from "./pages/dashboard/Equipment";
import NewRequest from "./pages/dashboard/NewRequest";
import Notifications from "./pages/dashboard/Notifications";
import Overview from "./pages/dashboard/Overview";
import Profile from "./pages/dashboard/Profile";
import Reports from "./pages/dashboard/Reports";
import RequestDetailPage from "./pages/dashboard/RequestDetail";
import Requests from "./pages/dashboard/Requests";
import ReviewQueue from "./pages/dashboard/ReviewQueue";
import Landing from "./pages/public/Landing";
import Login from "./pages/public/Login";
import Register from "./pages/public/Register";
import { VIEW_REQUESTS } from "./utils/navigation";

export default function App() {
  return (
    <Routes>
      {/* Public pages */}
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />

      {/* Dashboard: every route needs a signed-in user; some need a permission too */}
      <Route path="/app" element={<ProtectedRoute><DashboardLayout /></ProtectedRoute>}>
        <Route index element={<Overview />} />
        <Route path="requests" element={<ProtectedRoute anyOf={VIEW_REQUESTS}><Requests /></ProtectedRoute>} />
        <Route path="requests/new" element={<ProtectedRoute anyOf={["request.create"]}><NewRequest /></ProtectedRoute>} />
        <Route path="requests/:id" element={<ProtectedRoute anyOf={VIEW_REQUESTS}><RequestDetailPage /></ProtectedRoute>} />
        <Route path="queue" element={<ProtectedRoute anyOf={["request.review"]}><ReviewQueue /></ProtectedRoute>} />
        <Route path="equipment" element={<ProtectedRoute anyOf={["equipment.manage"]}><Equipment /></ProtectedRoute>} />
        <Route path="reports" element={<ProtectedRoute anyOf={["report.view"]}><Reports /></ProtectedRoute>} />
        <Route path="users" element={<ProtectedRoute anyOf={["user.manage"]}><UsersPage /></ProtectedRoute>} />
        <Route path="roles" element={<ProtectedRoute anyOf={["user.manage"]}><RolesPage /></ProtectedRoute>} />
        <Route path="settings" element={<ProtectedRoute anyOf={["settings.manage"]}><CompanySettings /></ProtectedRoute>} />
        <Route path="audit" element={<ProtectedRoute anyOf={["audit.view"]}><AuditLog /></ProtectedRoute>} />
        <Route path="notifications" element={<Notifications />} />
        <Route path="profile" element={<Profile />} />
        <Route path="*" element={<Navigate to="/app" replace />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
