import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { LoadingSpinner } from './UI';

/**
 * ProtectedRoute — Wraps any route that requires authentication.
 *
 * While the session check is in-flight (loading=true), renders a spinner
 * so we don't flash a redirect before we know if the cookie is valid.
 * After the check, unauthenticated users are redirected to /login with
 * the intended destination preserved in location state.
 */
export default function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <LoadingSpinner size="lg" message="Loading session..." />
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return children;
}
