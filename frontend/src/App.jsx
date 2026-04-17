// src/App.jsx
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { SessionProvider } from './context/SessionContext';
import { Nav } from './components/Nav';
import { LoginPage, RegisterPage } from './pages/AuthPage';
import { DashboardPage } from './pages/DashboardPage';
import { TopicsPage } from './pages/TopicsPage';
import { SessionPage } from './pages/SessionPage';
import { NotFoundPage } from './pages/NotFoundPage';
import { Loader } from './components/UI';

// ── Route guard ───────────────────────────────────────────────────────────────
// Redirects unauthenticated users to /login, preserving the intended destination
// so they land there after logging in.
function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  const location          = useLocation();

  if (loading) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Loader size="lg" label="Authenticating…" />
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return children;
}

// ── Guest route guard ─────────────────────────────────────────────────────────
// Redirects already-authenticated users away from login/register.
function GuestRoute({ children }) {
  const { user, loading } = useAuth();

  if (loading) return null;
  if (user)    return <Navigate to="/dashboard" replace />;

  return children;
}

// ── Shell layout ──────────────────────────────────────────────────────────────
// Nav is shown on all protected routes; hidden on auth pages.
function AppShell() {
  const { user } = useAuth();

  return (
    <>
      {user && <Nav />}
      <main style={{ flex: 1 }}>
        <Routes>
          {/* ── Public ──────────────────────────────────────────────────── */}
          <Route path="/" element={<Navigate to="/dashboard" replace />} />

          <Route path="/login" element={
            <GuestRoute><LoginPage /></GuestRoute>
          } />
          <Route path="/register" element={
            <GuestRoute><RegisterPage /></GuestRoute>
          } />

          {/* ── Protected ───────────────────────────────────────────────── */}
          <Route path="/dashboard" element={
            <ProtectedRoute><DashboardPage /></ProtectedRoute>
          } />

          <Route path="/topics" element={
            <ProtectedRoute><TopicsPage /></ProtectedRoute>
          } />

          <Route path="/topics/:topicId" element={
            <ProtectedRoute><TopicsPage /></ProtectedRoute>
          } />

          {/* Session route — wrapped in SessionProvider so context is
              isolated to one active session at a time */}
          <Route path="/session/:subtopicId" element={
            <ProtectedRoute>
              <SessionProvider>
                <SessionPage />
              </SessionProvider>
            </ProtectedRoute>
          } />

          {/* ── Fallback ─────────────────────────────────────────────────── */}
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </main>
    </>
  );
}

// ── Root ──────────────────────────────────────────────────────────────────────
export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppShell />
      </AuthProvider>
    </BrowserRouter>
  );
}
