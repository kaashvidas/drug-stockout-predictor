import { Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import LoginPage from "./pages/LoginPage";
import Dashboard from "./pages/Dashboard";
import type { Role } from "./types";

const ROLES: Role[] = ["facility", "district", "state", "program", "national"];

function ProtectedRoute({ role, children }: { role: Role; children: React.ReactNode }) {
  const { auth } = useAuth();
  if (!auth) return <Navigate to="/login" replace />;
  if (auth.role !== role) return <Navigate to={`/${auth.role}`} replace />;
  return <>{children}</>;
}

function AppRoutes() {
  const { auth } = useAuth();
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      {ROLES.map((role) => (
        <Route
          key={role}
          path={`/${role}`}
          element={
            <ProtectedRoute role={role}>
              <Dashboard />
            </ProtectedRoute>
          }
        />
      ))}
      <Route path="/" element={<Navigate to={auth ? `/${auth.role}` : "/login"} replace />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  );
}
