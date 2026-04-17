"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Sidebar } from "./Sidebar";
import { useAuthStore } from "@/store/auth";

export function AppShell({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, fetchMe } = useAuthStore();
  const router = useRouter();

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      router.push("/auth/login");
      return;
    }
    if (!isAuthenticated) {
      fetchMe().catch(() => router.push("/auth/login"));
    }
  }, []);

  if (!isAuthenticated) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="flex flex-col items-center gap-4">
          <div className="w-10 h-10 rounded-xl btn-brand flex items-center justify-center animate-pulse">
            <span className="text-white font-bold text-lg">C</span>
          </div>
          <div className="shimmer w-32 h-2 rounded" />
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-y-auto" style={{ marginLeft: "260px" }}>
        <div className="min-h-screen">
          {children}
        </div>
      </main>
    </div>
  );
}
