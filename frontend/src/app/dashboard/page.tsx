"use client";
import { AppShell } from "@/components/layout/AppShell";
import { useQuery } from "@tanstack/react-query";
import { transactionsApi, accountsApi, cashflowApi, subscriptionsApi, analyticsApi } from "@/lib/api";
import { Card, StatCard, Badge, EmptyState, PageHeader } from "@/components/ui";
import { formatCurrency, currentMonthYear, formatMonthYear, cn } from "@/lib/utils";
import {
  ArrowUpRight, ArrowDownRight, Wallet, TrendingUp, PiggyBank,
  AlertTriangle, Repeat, Sparkles, Activity, CreditCard, Target,
} from "lucide-react";
import { PieChart, Pie, Cell, BarChart, Bar, LineChart, Line, XAxis, YAxis, ResponsiveContainer, Tooltip, Legend, Area, AreaChart } from "recharts";
import { useState } from "react";

const CAT_COLORS = ["#22c55e", "#16a34a", "#059669", "#0d9488", "#0891b2", "#0284c7", "#6366f1", "#8b5cf6", "#ec4899", "#f43f5e"];

export default function DashboardPage() {
  const { month, year } = currentMonthYear();
  const [selectedPeriod, setSelectedPeriod] = useState({ month, year });

  const { data: summary, isLoading: loadSummary } = useQuery({
    queryKey: ["summary", selectedPeriod],
    queryFn: () => transactionsApi.summary(selectedPeriod),
  });

  const { data: accounts } = useQuery({ queryKey: ["accounts"], queryFn: () => accountsApi.list() });
  const { data: cashflow } = useQuery({ queryKey: ["cashflow"], queryFn: () => cashflowApi.predict(90) });
  const { data: subs } = useQuery({ queryKey: ["subs"], queryFn: () => subscriptionsApi.list() });
  const { data: trends } = useQuery({ queryKey: ["trends"], queryFn: () => analyticsApi.categoryTrends(3) });
  const { data: monthly } = useQuery({ queryKey: ["monthly"], queryFn: () => analyticsApi.monthlyComparison(6) });

  const totalBalance = accounts?.total_balance || 0;
  const savingsRate = summary?.income > 0 ? ((summary.income - summary.expense) / summary.income * 100) : 0;
  const activeSubscriptions = subs?.subscriptions?.filter((s: any) => s.status === "active") || [];

  return (
    <AppShell>
      <div className="p-8 max-w-[1600px] mx-auto">
        <PageHeader
          title="Dashboard"
          description={`Resumo financeiro de ${formatMonthYear(selectedPeriod.month, selectedPeriod.year)}`}
          actions={
            <Badge variant="success">
              <Activity size={12} className="mr-1" /> Tempo real
            </Badge>
          }
        />

        {/* KPI Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <StatCard
            title="Saldo Total"
            value={formatCurrency(totalBalance)}
            icon={<Wallet size={16} />}
            subtitle={`${accounts?.accounts?.length || 0} contas ativas`}
            color="#22c55e"
            loading={loadSummary}
          />
          <StatCard
            title="Receitas do Mês"
            value={formatCurrency(summary?.income || 0)}
            icon={<ArrowUpRight size={16} />}
            color="#22c55e"
            loading={loadSummary}
          />
          <StatCard
            title="Despesas do Mês"
            value={formatCurrency(summary?.expense || 0)}
            icon={<ArrowDownRight size={16} />}
            color="#f43f5e"
            loading={loadSummary}
          />
          <StatCard
            title="Taxa de Economia"
            value={`${savingsRate.toFixed(1)}%`}
            icon={<Target size={16} />}
            subtitle={savingsRate > 20 ? "Excelente! 🎉" : savingsRate > 10 ? "Bom caminho" : "Atenção"}
            color={savingsRate > 20 ? "#22c55e" : savingsRate > 10 ? "#f59e0b" : "#f43f5e"}
            loading={loadSummary}
          />
        </div>

        {/* Alerts */}
        {cashflow?.alerts && cashflow.alerts.length > 0 && (
          <div className="mb-8 space-y-2">
            {cashflow.alerts.slice(0, 3).map((a: any, i: number) => (
              <div key={i} className="flex items-start gap-3 p-4 rounded-xl animate-fade-up" style={{
                background: a.type === "danger" ? "rgba(244,63,94,0.1)" : a.type === "warning" ? "rgba(245,158,11,0.1)" : "rgba(34,197,94,0.1)",
                border: a.type === "danger" ? "1px solid rgba(244,63,94,0.2)" : a.type === "warning" ? "1px solid rgba(245,158,11,0.2)" : "1px solid rgba(34,197,94,0.2)",
              }}>
                <AlertTriangle size={16} className="flex-shrink-0 mt-0.5" style={{
                  color: a.type === "danger" ? "#f43f5e" : a.type === "warning" ? "#f59e0b" : "#22c55e",
                }} />
                <p className="text-sm text-gray-200">{a.message}</p>
              </div>
            ))}
          </div>
        )}

        {/* Main charts row */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-8">
          {/* Evolution chart */}
          <Card className="lg:col-span-2">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-base font-semibold text-white">Evolução Mensal</h3>
                <p className="text-xs text-gray-500">Últimos 6 meses</p>
              </div>
            </div>
            <ResponsiveContainer width="100%" height={280}>
              <AreaChart data={monthly || []}>
                <defs>
                  <linearGradient id="gInc" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#22c55e" stopOpacity={0.3} />
                    <stop offset="100%" stopColor="#22c55e" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="gExp" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#f43f5e" stopOpacity={0.3} />
                    <stop offset="100%" stopColor="#f43f5e" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="label" stroke="#6b7280" fontSize={11} tickLine={false} axisLine={false} />
                <YAxis stroke="#6b7280" fontSize={11} tickLine={false} axisLine={false}
                  tickFormatter={(v) => `R$ ${(v / 1000).toFixed(0)}k`} />
                <Tooltip
                  contentStyle={{ background: "#22262f", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8 }}
                  formatter={(v: any) => formatCurrency(v as number)}
                  labelStyle={{ color: "#fff" }}
                />
                <Area type="monotone" dataKey="income" stroke="#22c55e" fill="url(#gInc)" strokeWidth={2} name="Receita" />
                <Area type="monotone" dataKey="expense" stroke="#f43f5e" fill="url(#gExp)" strokeWidth={2} name="Despesa" />
              </AreaChart>
            </ResponsiveContainer>
          </Card>

          {/* Expense by category */}
          <Card>
            <h3 className="text-base font-semibold text-white mb-1">Gastos por Categoria</h3>
            <p className="text-xs text-gray-500 mb-4">Distribuição do mês</p>
            {summary?.by_category && summary.by_category.length > 0 ? (
              <>
                <ResponsiveContainer width="100%" height={180}>
                  <PieChart>
                    <Pie
                      data={summary.by_category.slice(0, 6)}
                      dataKey="total" nameKey="name" cx="50%" cy="50%"
                      innerRadius={45} outerRadius={80} paddingAngle={2}
                    >
                      {summary.by_category.slice(0, 6).map((_: any, i: number) => (
                        <Cell key={i} fill={CAT_COLORS[i % CAT_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(v: any) => formatCurrency(v as number)}
                      contentStyle={{ background: "#22262f", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8 }} />
                  </PieChart>
                </ResponsiveContainer>
                <div className="space-y-1.5 mt-3">
                  {summary.by_category.slice(0, 5).map((c: any, i: number) => (
                    <div key={i} className="flex items-center gap-2 text-xs">
                      <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: CAT_COLORS[i % CAT_COLORS.length] }} />
                      <span className="flex-1 text-gray-400 truncate">{c.name}</span>
                      <span className="text-gray-200 font-medium number-display">{formatCurrency(c.total)}</span>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <EmptyState title="Sem dados" description="Adicione lançamentos para ver a distribuição" />
            )}
          </Card>
        </div>

        {/* Widgets row */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Top spending categories with growth */}
          <Card>
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-base font-semibold text-white">Categorias em Alta</h3>
                <p className="text-xs text-gray-500">Maior crescimento</p>
              </div>
              <TrendingUp size={16} className="text-amber-400" />
            </div>
            <div className="space-y-3">
              {trends?.slice(0, 5).map((t: any, i: number) => (
                <div key={i} className="flex items-center gap-3 p-2 rounded-lg hover:bg-white/5 transition-colors">
                  <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
                    style={{ background: t.color + "20" }}>
                    <div className="w-2 h-2 rounded-full" style={{ background: t.color }} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-white truncate">{t.name}</p>
                    <p className="text-xs text-gray-500">{formatCurrency(t.avg_monthly)}/mês</p>
                  </div>
                  <Badge variant={t.growth_pct > 0 ? "danger" : "success"}>
                    {t.growth_pct > 0 ? "+" : ""}{t.growth_pct}%
                  </Badge>
                </div>
              ))}
              {(!trends || trends.length === 0) && <EmptyState title="Sem dados de tendência" />}
            </div>
          </Card>

          {/* Active subscriptions */}
          <Card>
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-base font-semibold text-white">Assinaturas Ativas</h3>
                <p className="text-xs text-gray-500">{activeSubscriptions.length} detectadas</p>
              </div>
              <Repeat size={16} className="text-violet-400" />
            </div>
            <div className="space-y-2">
              {activeSubscriptions.slice(0, 5).map((s: any) => (
                <div key={s.id} className="flex items-center justify-between p-2 rounded-lg hover:bg-white/5">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-white truncate">{s.name}</p>
                    <p className="text-xs text-gray-500">{s.frequency_label}</p>
                  </div>
                  <span className="text-sm font-semibold text-white number-display">{formatCurrency(s.amount)}</span>
                </div>
              ))}
              {activeSubscriptions.length === 0 && (
                <EmptyState title="Nenhuma assinatura detectada" description="Importe extratos para detecção automática" />
              )}
              {activeSubscriptions.length > 0 && (
                <div className="pt-3 mt-3 border-t flex items-center justify-between" style={{ borderColor: "var(--color-border)" }}>
                  <span className="text-xs text-gray-500">Total mensal</span>
                  <span className="text-sm font-bold text-white number-display">
                    {formatCurrency(subs?.total_monthly || 0)}
                  </span>
                </div>
              )}
            </div>
          </Card>

          {/* Cashflow prediction */}
          <Card>
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-base font-semibold text-white">Previsão 90 dias</h3>
                <p className="text-xs text-gray-500">Baseado em padrões</p>
              </div>
              <Sparkles size={16} className="text-green-400" />
            </div>
            {cashflow?.projections && cashflow.projections.length > 0 ? (
              <>
                <ResponsiveContainer width="100%" height={140}>
                  <LineChart data={cashflow.projections}>
                    <Line type="monotone" dataKey="projected_balance" stroke="#22c55e" strokeWidth={2} dot={false} />
                    <XAxis dataKey="date" hide />
                    <YAxis hide />
                    <Tooltip
                      formatter={(v: any) => formatCurrency(v as number)}
                      contentStyle={{ background: "#22262f", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
                <div className="grid grid-cols-2 gap-3 mt-4 pt-4 border-t" style={{ borderColor: "var(--color-border)" }}>
                  <div>
                    <p className="text-xs text-gray-500 mb-0.5">Receita média</p>
                    <p className="text-sm font-bold text-income number-display">{formatCurrency(cashflow.avg_monthly_income)}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500 mb-0.5">Despesa média</p>
                    <p className="text-sm font-bold text-expense number-display">{formatCurrency(cashflow.avg_monthly_expense)}</p>
                  </div>
                  {cashflow.potential_monthly_savings > 0 && (
                    <div className="col-span-2 mt-2 p-3 rounded-lg" style={{ background: "rgba(34,197,94,0.1)" }}>
                      <p className="text-xs text-gray-400 mb-0.5">💰 Economia potencial</p>
                      <p className="text-sm font-bold text-income number-display">{formatCurrency(cashflow.potential_monthly_savings)}/mês</p>
                    </div>
                  )}
                </div>
              </>
            ) : (
              <EmptyState title="Sem dados suficientes" description="Adicione ao menos 30 dias de transações" />
            )}
          </Card>
        </div>

        {/* Accounts grid */}
        {accounts?.accounts && accounts.accounts.length > 0 && (
          <div className="mt-8">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-base font-semibold text-white">Suas Contas</h3>
              <Badge>{accounts.accounts.length}</Badge>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {accounts.accounts.map((a: any) => (
                <div key={a.id} className="card p-4 relative overflow-hidden group cursor-pointer hover:border-brand-500/30 transition-colors">
                  <div className="absolute top-0 right-0 w-20 h-20 rounded-full blur-2xl opacity-20" style={{ background: a.color }} />
                  <div className="relative">
                    <div className="flex items-center justify-between mb-3">
                      <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: a.color + "20", color: a.color }}>
                        <CreditCard size={14} />
                      </div>
                      <Badge variant="neutral">{a.type}</Badge>
                    </div>
                    <p className="text-xs text-gray-500 mb-1">{a.bank_name || a.name}</p>
                    <p className="text-lg font-bold text-white number-display">{formatCurrency(a.balance)}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
