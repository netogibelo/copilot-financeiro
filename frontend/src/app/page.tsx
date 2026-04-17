"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/store/auth";
import { Zap } from "lucide-react";

export default function HomePage() {
  const router = useRouter();
  const { isAuthenticated } = useAuthStore();

  useEffect(() => {
    const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
    router.replace(token ? "/dashboard" : "/auth/login");
  }, [router]);

  return (
    <div className="h-screen flex items-center justify-center">
      <div className="flex flex-col items-center gap-4">
        <div className="w-12 h-12 rounded-xl btn-brand flex items-center justify-center animate-pulse">
          <Zap size={20} className="text-white" />
        </div>
        <p className="text-sm text-gray-500">Carregando Copilot Financeiro...</p>
      </div>
    </div>
  );
}
