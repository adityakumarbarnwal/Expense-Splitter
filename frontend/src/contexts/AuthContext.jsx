import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import apiClient from '../services/api';

/**
 * AuthContext — Central authentication state for the app.
 *
 * Session is restored on mount by calling GET /api/v1/auth/me.
 * JWT is stored in an httpOnly cookie managed by the backend — NOT localStorage.
 */
const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true); // true while session check is in flight

  // Restore session on mount
  const checkSession = useCallback(async () => {
    try {
      const res = await apiClient.get('/auth/me');
      setUser(res.data.user ?? res.data);
    } catch {
      setUser(null);
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
    try {
      await apiClient.post('/auth/logout');
    } catch {
      // ignore errors — still clear local state
    } finally {
      setUser(null);
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
