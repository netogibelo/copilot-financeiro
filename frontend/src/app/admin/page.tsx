"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { AppShell } from "@/components/layout/AppShell";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { adminApi } from "@/lib/api";
import { useAuthStore } from "@/store/auth";
import { Card, Button, Badge, PageHeader, StatCard, Input, Spinner } from "@/components/ui";
import { Users, CreditCard, Activity, FileText, Shield, Ban, Key, Search, RefreshCw, ChevronRight } from "lucide-react";
import * as Tabs from "@radix-ui/react-tabs";
import toast from "react-hot-toast";
import { formatDate, formatCurrency } from "@/lib/utils";

export default function AdminPage() {
  const { user } = useAuthStore();
  const router = useRouter();
  const [tab, setTab] = useState("overview");

  useEffect(() => {
    if (user && user.role !== "admin") router.push("/dashboard");
  }, [user, router]);

  if (!user || user.role !== "admin") return null;

  return (
    <AppShell>
      <div className="p-8 max-w-[1600px] mx-auto">
        <PageHeader
          title="Painel de Administração"
          description="Gerencie usuários, transações e configurações do sistema"
          actions={<Badge variant="purple"><Shield size={12} className="mr-1" />Admin</Badge>}
        />

        <Tabs.Root value={tab} onValueChange={setTab}>
          <Tabs.List className="flex gap-1 p-1 rounded-xl mb-6 w-fit overflow-x-auto" style={{ background: "var(--color-surface-1)", border: "1px solid var(--color-border)" }}>
            {[
              { value: "overview", label: "Visão Geral" },
              { value: "users", label: "Usuários" },
              { value: "transactions", label: "Transações" },
              { value: "categories", label: "Categorias" },
              { value: "imports", label: "Importações" },
              { value: "audit", label: "Auditoria" },
            ].map((t) => (
              <Tabs.Trigger key={t.value} value={t.value}
                className="px-4 py-2 rounded-lg text-sm font-medium text-gray-400 data-[state=active]:text-white whitespace-nowrap"
                style={tab === t.value ? { background: "rgba(34,197,94,0.15)", color: "#22c55e" } : {}}
              >
                {t.label}
              </Tabs.Trigger>
            ))}
          </Tabs.List>

          <Tabs.Content value="overview"><OverviewTab /></Tabs.Content>
          <Tabs.Content value="users"><UsersTab /></Tabs.Content>
          <Tabs.Content value="transactions"><TransactionsTab /></Tabs.Content>
          <Tabs.Content value="categories"><CategoriesTab /></Tabs.Content>
          <Tabs.Content value="imports"><ImportsTab /></Tabs.Content>
          <Tabs.Content value="audit"><AuditTab /></Tabs.Content>
        </Tabs.Root>
      </div>
    </AppShell>
  );
}

function OverviewTab() {
  const { data: stats, isLoading } = useQuery({ queryKey: ["admin-stats"], queryFn: () => adminApi.stats() });

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      <StatCard title="Usuários Totais" value={String(stats?.total_users || 0)}
        subtitle={`${stats?.active_users || 0} ativos`} icon={<Users size={16} />} loading={isLoading} />
      <StatCard title="Contas" value={String(stats?.total_accounts || 0)}
        icon={<CreditCard size={16} />} loading={isLoading} />
      <StatCard title="Transações" value={String(stats?.total_transactions || 0)}
        icon={<Activity size={16} />} loading={isLoading} />
      <StatCard title="Importações" value={String(stats?.total_imports || 0)}
        icon={<FileText size={16} />} loading={isLoading} />
    </div>
  );
}

function UsersTab() {
  const qc = useQueryClient();
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);

  const { data, isLoading } = useQuery({
    queryKey: ["admin-users", search, page],
    queryFn: () => adminApi.users({ search: search || undefined, page, per_page: 20 }),
  });

  const blockMut = useMutation({
    mutationFn: (id: string) => adminApi.blockUser(id),
    onSuccess: () => { toast.success("Usuário atualizado"); qc.invalidateQueries({ queryKey: ["admin-users"] }); },
  });

  const resetMut = useMutation({
    mutationFn: (id: string) => adminApi.resetUserPassword(id),
    onSuccess: (d) => toast.success(`Senha temporária: ${d.temp_password}`),
  });

  return (
    <div className="space-y-4">
      <div className="relative max-w-md">
        <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
        <input placeholder="Buscar por nome ou email..." value={search} onChange={(e) => setSearch(e.target.value)}
          className="w-full h-10 rounded-xl border text-sm text-white pl-10 pr-3 focus:outline-none"
          style={{ background: "var(--color-surface-2)", borderColor: "var(--color-border)" }}
        />
      </div>
      <Card className="p-0">
        {isLoading ? <div className="p-12 flex justify-center"><Spinner /></div> : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b" style={{ borderColor: "var(--color-border)" }}>
                  <th className="text-left p-3 text-xs uppercase text-gray-500">Nome</th>
                  <th className="text-left p-3 text-xs uppercase text-gray-500">Email</th>
                  <th className="text-left p-3 text-xs uppercase text-gray-500">Role</th>
                  <th className="text-left p-3 text-xs uppercase text-gray-500">Status</th>
                  <th className="text-left p-3 text-xs uppercase text-gray-500">Último login</th>
                  <th className="p-3"></th>
                </tr>
              </thead>
              <tbody>
                {data?.data?.map((u: any) => (
                  <tr key={u.id} className="border-b hover:bg-white/[0.02]" style={{ borderColor: "var(--color-border)" }}>
                    <td className="p-3 text-white font-medium">{u.name}</td>
                    <td className="p-3 text-gray-400">{u.email}</td>
                    <td className="p-3">
                      <Badge variant={u.role === "admin" ? "purple" : "neutral"}>{u.role}</Badge>
                    </td>
                    <td className="p-3">
                      <Badge variant={u.is_active ? "success" : "danger"}>
                        {u.is_active ? "Ativo" : "Bloqueado"}
                      </Badge>
                    </td>
                    <td className="p-3 text-gray-500 text-xs">
                      {u.last_login_at ? formatDate(u.last_login_at) : "Nunca"}
                    </td>
                    <td className="p-3">
                      <div className="flex items-center justify-end gap-1">
                        <button onClick={() => confirm("Alterar status?") && blockMut.mutate(u.id)}
                          className="p-1.5 rounded-lg hover:bg-white/5 text-amber-400" title="Bloquear/Desbloquear">
                          <Ban size={12} />
                        </button>
                        <button onClick={() => confirm("Redefinir senha?") && resetMut.mutate(u.id)}
                          className="p-1.5 rounded-lg hover:bg-white/5 text-blue-400" title="Redefinir senha">
                          <Key size={12} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}

function TransactionsTab() {
  const { data, isLoading } = useQuery({ queryKey: ["admin-txns"], queryFn: () => adminApi.transactions({ per_page: 30 }) });
  return (
    <Card className="p-0">
      {isLoading ? <div className="p-12 flex justify-center"><Spinner /></div> : (
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b" style={{ borderColor: "var(--color-border)" }}>
              <th className="text-left p-3 text-xs uppercase text-gray-500">Data</th>
              <th className="text-left p-3 text-xs uppercase text-gray-500">Descrição</th>
              <th className="text-left p-3 text-xs uppercase text-gray-500">Tipo</th>
              <th className="text-right p-3 text-xs uppercase text-gray-500">Valor</th>
            </tr>
          </thead>
          <tbody>
            {data?.data?.map((t: any) => (
              <tr key={t.id} className="border-b" style={{ borderColor: "var(--color-border)" }}>
                <td className="p-3 text-gray-400">{formatDate(t.date)}</td>
                <td className="p-3 text-white">{t.description}</td>
                <td className="p-3"><Badge variant={t.type === "receita" ? "success" : "danger"}>{t.type}</Badge></td>
                <td className="p-3 text-right text-white font-semibold">{formatCurrency(t.amount)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Card>
  );
}

function CategoriesTab() {
  const { data, isLoading } = useQuery({ queryKey: ["admin-cats"], queryFn: () => adminApi.categories() });
  return (
    <Card className="p-0">
      {isLoading ? <div className="p-12 flex justify-center"><Spinner /></div> : (
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b" style={{ borderColor: "var(--color-border)" }}>
              <th className="text-left p-3 text-xs uppercase text-gray-500">Nome</th>
              <th className="text-left p-3 text-xs uppercase text-gray-500">Tipo</th>
              <th className="text-left p-3 text-xs uppercase text-gray-500">Sistema</th>
            </tr>
          </thead>
          <tbody>
            {data?.map((c: any) => (
              <tr key={c.id} className="border-b" style={{ borderColor: "var(--color-border)" }}>
                <td className="p-3">
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full" style={{ background: c.color }} />
                    <span className="text-white">{c.name}</span>
                  </div>
                </td>
                <td className="p-3 text-gray-400 capitalize">{c.type}</td>
                <td className="p-3">{c.is_system ? <Badge variant="info">Sistema</Badge> : <Badge>Usuário</Badge>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Card>
  );
}

function ImportsTab() {
  const { data, isLoading } = useQuery({ queryKey: ["admin-imports"], queryFn: () => adminApi.imports() });
  return (
    <Card className="p-0">
      {isLoading ? <div className="p-12 flex justify-center"><Spinner /></div> : (
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b" style={{ borderColor: "var(--color-border)" }}>
              <th className="text-left p-3 text-xs uppercase text-gray-500">Arquivo</th>
              <th className="text-left p-3 text-xs uppercase text-gray-500">Tipo</th>
              <th className="text-left p-3 text-xs uppercase text-gray-500">Status</th>
              <th className="text-left p-3 text-xs uppercase text-gray-500">Transações</th>
              <th className="text-left p-3 text-xs uppercase text-gray-500">Data</th>
            </tr>
          </thead>
          <tbody>
            {data?.data?.map((i: any) => (
              <tr key={i.id} className="border-b" style={{ borderColor: "var(--color-border)" }}>
                <td className="p-3 text-white">{i.filename}</td>
                <td className="p-3 text-gray-400">{i.file_type}</td>
                <td className="p-3">
                  <Badge variant={i.status === "completed" ? "success" : i.status === "failed" ? "danger" : "warning"}>
                    {i.status}
                  </Badge>
                </td>
                <td className="p-3 text-gray-300">{i.imported_transactions}/{i.total_transactions}</td>
                <td className="p-3 text-gray-500 text-xs">{formatDate(i.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Card>
  );
}

function AuditTab() {
  const { data, isLoading } = useQuery({ queryKey: ["admin-audit"], queryFn: () => adminApi.auditLogs() });
  return (
    <Card className="p-0">
      {isLoading ? <div className="p-12 flex justify-center"><Spinner /></div> : (
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b" style={{ borderColor: "var(--color-border)" }}>
              <th className="text-left p-3 text-xs uppercase text-gray-500">Data</th>
              <th className="text-left p-3 text-xs uppercase text-gray-500">Ação</th>
              <th className="text-left p-3 text-xs uppercase text-gray-500">Entidade</th>
              <th className="text-left p-3 text-xs uppercase text-gray-500">Detalhes</th>
            </tr>
          </thead>
          <tbody>
            {data?.data?.map((l: any) => (
              <tr key={l.id} className="border-b" style={{ borderColor: "var(--color-border)" }}>
                <td className="p-3 text-gray-500 text-xs">{formatDate(l.created_at)}</td>
                <td className="p-3"><Badge variant="info">{l.action}</Badge></td>
                <td className="p-3 text-gray-400">{l.entity_type}</td>
                <td className="p-3 text-gray-600 text-xs truncate max-w-xs">
                  {l.details ? JSON.stringify(l.details).slice(0, 60) : "-"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Card>
  );
}
