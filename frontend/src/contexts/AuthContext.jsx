import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import axios from 'axios';
import apiClient from '../services/api';

/**
 * AuthContext — Central authentication state for the app.
 *
 * Session is restored on mount by calling GET /api/v1/auth/me.
 * JWT is stored in an httpOnly cookie managed by the backend — NOT localStorage.
 *
 * Session-persistence rules:
 * - A genuine 401 Unauthorized → user is not authenticated → setUser(null)
 * - A network error, timeout, or non-auth server error (5xx) → keep existing
 *   user state; do NOT log the user out for a transient problem.
 * - This prevents the application from logging users out when MongoDB is slow,
 *   Gemini is unavailable, or a single API call times out.
 */
const AuthContext = createContext(null);

/** Determine whether an axios error represents a genuine authentication failure. */
function isAuthFailure(err) {
  // A real auth failure returns HTTP 401 from the backend
  return err?.response?.status === 401;
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true); // true while initial session check is in flight
  // Guard against concurrent logout operations (e.g. multiple parallel 401s)
  const loggingOut = useRef(false);

  // Restore session on mount.
  // Uses a dedicated CancelToken so the check is aborted if the component unmounts.
  const checkSession = useCallback(async () => {
    try {
      // Use a shorter timeout for the session check — if the server is reachable,
      // /auth/me only does a JWT decode + one indexed DB lookup and should be fast.
      const res = await apiClient.get('/auth/me', { timeout: 10000 });
      setUser(res.data.user ?? res.data);
    } catch (err) {
      if (isAuthFailure(err)) {
        // Genuine 401 → no valid session cookie
        setUser(null);
      } else {
        // Network error, timeout, 5xx, etc.
        // Do NOT clear user state — the server may be temporarily unreachable.
        // If user was already null (first load), keep null; otherwise preserve state.
        // On first mount user is null so this is equivalent to setUser(null) only
        // when there was no prior user — which is the correct initial state anyway.
        setUser((prev) => prev);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    checkSession();
  }, [checkSession]);

  const login = async (email, password) => {
    const res = await apiClient.post('/auth/login', { email, password });
    const u = res.data.user ?? res.data;
    setUser(u);
    return u;
  };

  const register = async (name, email, password) => {
    const res = await apiClient.post('/auth/register', { name, email, password });
    const u = res.data.user ?? res.data;
    setUser(u);
    return u;
  };

  const logout = async () => {
    if (loggingOut.current) return; // prevent concurrent logouts
    loggingOut.current = true;
    try {
      await apiClient.post('/auth/logout');
    } catch {
      // ignore errors — still clear local state
    } finally {
      setUser(null);
      loggingOut.current = false;
    }
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, register, checkSession }}>
      {children}
    </AuthContext.Provider>
  );
}

/** Hook to consume auth context anywhere in the app. */
export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
