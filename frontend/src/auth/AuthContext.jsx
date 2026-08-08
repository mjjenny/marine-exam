import { createContext, useContext, useEffect, useState, useCallback } from "react";
import { api, ApiError } from "../api/client.js";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // Restore session on load.
  useEffect(() => {
    api
      .me()
      .then(setUser)
      .catch((err) => {
        if (!(err instanceof ApiError && err.status === 401)) {
          console.error("session check failed", err);
        }
        setUser(null);
      })
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (email, password) => {
    const u = await api.login(email, password);
    setUser(u);
    return u;
  }, []);

  const signup = useCallback((email, password) => api.signup(email, password), []);

  const logout = useCallback(async () => {
    await api.logout();
    setUser(null);
  }, []);

  // Re-pull the current user from the server — used after a profile change (e.g.
  // setting the exam date on My Account) so dependents like Home's countdown pick
  // it up immediately without a full reload.
  const refreshUser = useCallback(async () => {
    const u = await api.me();
    setUser(u);
    return u;
  }, []);

  const value = { user, loading, login, signup, logout, refreshUser };
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
