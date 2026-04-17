// src/context/AuthContext.jsx
import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { authAPI, tokenStore } from '../api/client';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user,    setUser]    = useState(null);
  const [loading, setLoading] = useState(true);  // true until initial token check

  // On mount: restore user from token if one exists
  useEffect(() => {
    const token = tokenStore.getAccess();
    if (token) {
      try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        if (payload.exp * 1000 > Date.now()) {
          setUser({ user_id: payload.sub });
        } else {
          tokenStore.clear();
        }
      } catch {
        tokenStore.clear();
      }
    }
    setLoading(false);
  }, []);

  const login = useCallback(async (email, password) => {
    const data = await authAPI.login(email, password);
    tokenStore.set(data.access_token, data.refresh_token);
    setUser({ user_id: data.user_id, username: data.username });
    return data;
  }, []);

  const register = useCallback(async (username, email, password) => {
    const data = await authAPI.register(username, email, password);
    tokenStore.set(data.access_token, data.refresh_token);
    setUser({ user_id: data.user_id, username: data.username });
    return data;
  }, []);

  const logout = useCallback(async () => {
    try { await authAPI.logout(); } catch { /* best effort */ }
    tokenStore.clear();
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider');
  return ctx;
};
