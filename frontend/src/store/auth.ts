import { create } from "zustand";
import { persist } from "zustand/middleware";
import { authApi } from "@/lib/api";

interface User {
  id: string;
  name: string;
  email: string;
  role: "user" | "admin";
  avatar_url?: string;
}

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  loginWithGoogle: (token: string) => Promise<void>;
  logout: () => void;
  fetchMe: () => Promise<void>;
  setTokens: (access: string, refresh: string, user: User) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      isAuthenticated: false,
      isLoading: false,

      setTokens: (access, refresh, user) => {
        if (typeof window !== "undefined") {
          localStorage.setItem("access_token", access);
          localStorage.setItem("refresh_token", refresh);
        }
        set({ user, isAuthenticated: true });
      },

      login: async (email, password) => {
        set({ isLoading: true });
        try {
          const data = await authApi.login(email, password);
          get().setTokens(data.access_token, data.refresh_token, data.user);
        } finally {
          set({ isLoading: false });
        }
      },

      loginWithGoogle: async (token) => {
        set({ isLoading: true });
        try {
          const data = await authApi.googleLogin(token);
          get().setTokens(data.access_token, data.refresh_token, data.user);
        } finally {
          set({ isLoading: false });
        }
      },

      logout: () => {
        if (typeof window !== "undefined") {
          localStorage.removeItem("access_token");
          localStorage.removeItem("refresh_token");
        }
        set({ user: null, isAuthenticated: false });
      },

      fetchMe: async () => {
        try {
          const user = await authApi.me();
          set({ user, isAuthenticated: true });
        } catch {
          get().logout();
        }
      },
    }),
    {
      name: "copilot-auth",
      partialize: (state) => ({ user: state.user, isAuthenticated: state.isAuthenticated }),
    }
  )
);
