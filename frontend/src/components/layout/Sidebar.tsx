"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  LayoutDashboard, CreditCard, ArrowUpDown, Upload, Tag,
  MessageSquare, Shield, BarChart3, LogOut, Settings,
  TrendingUp, Repeat, ChevronRight, Zap,
} from "lucide-react";
import { useAuthStore } from "@/store/auth";
import toast from "react-hot-toast";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { href: "/dashboard", icon: LayoutDashboard, label: "Dashboard" },
  { href: "/contas", icon: CreditCard, label: "Contas" },
  { href: "/financeiro", icon: ArrowUpDown, label: "Financeiro" },
  { href: "/importacoes", icon: Upload, label: "Importações" },
  { href: "/categorias", icon: Tag, label: "Categorias" },
  { href: "/consultor", icon: MessageSquare, label: "Consultor IA", badge: "IA" },
  { href: "/relatorios", icon: BarChart3, label: "Relatórios" },
];

const ADMIN_ITEMS = [
  { href: "/admin", icon: Shield, label: "Administração" },
];

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuthStore();

  const handleLogout = () => {
    logout();
    toast.success("Até logo!");
    router.push("/auth/login");
  };

  return (
    <aside className="fixed left-0 top-0 h-screen w-[260px] flex flex-col z-50"
      style={{ background: "var(--color-surface-1)", borderRight: "1px solid var(--color-border)" }}>

      {/* Logo */}
      <div className="flex items-center gap-3 px-5 h-16 border-b" style={{ borderColor: "var(--color-border)" }}>
        <div className="w-8 h-8 rounded-lg btn-brand flex items-center justify-center flex-shrink-0">
          <Zap size={16} className="text-white" />
        </div>
        <div>
          <p className="text-sm font-bold text-white leading-tight">Copilot</p>
          <p className="text-xs" style={{ color: "var(--color-text-muted)" }}>Financeiro</p>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-1">
        <p className="text-xs font-semibold px-3 mb-3 uppercase tracking-widest"
          style={{ color: "var(--color-text-muted)" }}>Menu</p>

        {NAV_ITEMS.map(({ href, icon: Icon, label, badge }) => {
          const active = pathname === href || pathname.startsWith(href + "/");
          return (
            <Link key={href} href={href} className={cn("nav-item", active && "active")}>
              <Icon size={16} className="flex-shrink-0" />
              <span className="flex-1">{label}</span>
              {badge && (
                <span className="text-xs px-1.5 py-0.5 rounded-md font-semibold"
                  style={{ background: "rgba(34,197,94,0.15)", color: "#22c55e", border: "1px solid rgba(34,197,94,0.2)" }}>
                  {badge}
                </span>
              )}
            </Link>
          );
        })}

        {user?.role === "admin" && (
          <>
            <div className="my-3 h-px" style={{ background: "var(--color-border)" }} />
            <p className="text-xs font-semibold px-3 mb-3 uppercase tracking-widest"
              style={{ color: "var(--color-text-muted)" }}>Admin</p>
            {ADMIN_ITEMS.map(({ href, icon: Icon, label }) => {
              const active = pathname.startsWith(href);
              return (
                <Link key={href} href={href} className={cn("nav-item", active && "active")}>
                  <Icon size={16} />
                  <span>{label}</span>
                </Link>
              );
            })}
          </>
        )}
      </nav>

      {/* User profile */}
      <div className="p-3 border-t" style={{ borderColor: "var(--color-border)" }}>
        <div className="flex items-center gap-3 p-2 rounded-xl cursor-pointer hover:bg-surface-2 transition-colors"
          style={{ background: "var(--color-surface-2)" }}>
          <div className="w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold flex-shrink-0"
            style={{ background: "linear-gradient(135deg, #22c55e, #15803d)", color: "white" }}>
            {user?.name?.charAt(0).toUpperCase()}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-white truncate">{user?.name}</p>
            <p className="text-xs truncate" style={{ color: "var(--color-text-muted)" }}>
              {user?.role === "admin" ? "Administrador" : "Usuário"}
            </p>
          </div>
          <button onClick={handleLogout} className="p-1.5 rounded-lg hover:bg-red-500/10 transition-colors"
            title="Sair">
            <LogOut size={14} style={{ color: "var(--color-text-muted)" }} />
          </button>
        </div>
      </div>
    </aside>
  );
}
