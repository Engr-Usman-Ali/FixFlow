import { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { Loading } from "../common/States";
import type { Permission } from "../../types";

interface Props { children: ReactNode; anyOf?: Permission[] }

/**
 * Keeps signed-out visitors out of /app and sends users away from pages they have
 * no permission for. This is a convenience only: the API enforces every permission.
 */
export default function ProtectedRoute({ children, anyOf }: Props) {
  const { user, loading, canAny } = useAuth();
  const location = useLocation();

  if (loading) return <Loading label="Checking your session" />;
  if (!user) return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  if (anyOf && !canAny(anyOf)) return <Navigate to="/app" replace />;
  return <>{children}</>;
}
