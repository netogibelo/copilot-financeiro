"use client";
import { useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { useQuery } from "@tanstack/react-query";
import { analyticsApi } from "@/lib/api";
import { Card, Input, Button, PageHeader, StatCard, Badge } from "@/components/ui";
import { formatCurrency } from "@/lib/utils";
import { Download, TrendingUp, TrendingDown, DollarSign, Target, Calendar } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";

export default function RelatoriosPage() {
  const today = new Date();
  const firstOfMonth = new Date(today.getFullYear(), today.getMonth(), 1);
  const [startDate, setStartDate] = useState(firstOfMonth.toISOString().split("T")[0]);
  const [endDate, setEndDate] = useState(today.toISOString().split("T")[0]);

  const { data: stmt } = useQuery({
    queryKey: ["report", startDate, endDate],
    queryFn: () => analyticsApi.cashflowStatement(startDate, endDate),
  });

  const { data: trends } = useQuery({ queryKey: ["trends6"], queryFn: () => analyticsApi.categoryTrends(6) });

  return (
    <AppShell>
      <div className="p-8 max-w-[1400px] mx-auto">
        <PageHeader title="Relatórios" description="Análises detalhadas e demonstrativos financeiros" />

        {/* Period filter */}
        <Card className="mb-6">
          <div className="flex flex-wrap items-end gap-3">
            <Input label="Data inicial" type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
            <Input label="Data final" type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
            <Button leftIcon={<Download size={14} />} variant="outline">Exportar</Button>
          </div>
        </Card>

        {/* Stats */}
        {stmt?.summary && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <StatCard title="Total Recebido" value={formatCurrency(stmt.summary.total_income)}
              icon={<TrendingUp size={16} />} color="#22c55e" />
            <StatCard title="Total Gasto" value={formatCurrency(stmt.summary.total_expense)}
              icon={<TrendingDown size={16} />} color="#f43f5e" />
            <StatCard title="Investido" value={formatCurrency(stmt.summary.total_investment)}
              icon={<DollarSign size={16} />} color="#8b5cf6" />
            <StatCard title="Taxa de Economia" value={`${stmt.summary.savings_rate}%`}
              icon={<Target size={16} />}
              subtitle={stmt.summary.savings_rate > 20 ? "Excelente!" : "Pode melhorar"}
              color={stmt.summary.savings_rate > 20 ? "#22c55e" : "#f59e0b"} />
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Expenses by category */}
          <Card>
            <h3 className="text-base font-semibold text-white mb-4">Top Categorias de Gastos</h3>
            {stmt?.expense_by_category && stmt.expense_by_category.length > 0 ? (
              <ResponsiveContainer width="100%" height={320}>
                <BarChart data={stmt.expense_by_category.slice(0, 8)} layout="vertical" margin={{ left: 90 }}>
                  <XAxis type="number" stroke="#6b7280" fontSize={11}
                    tickFormatter={(v) => `${(v/1000).toFixed(0)}k`} />
                  <YAxis type="category" dataKey="name" stroke="#6b7280" fontSize={11} width={85} />
                  <Tooltip formatter={(v: any) => formatCurrency(v as number)}
                    contentStyle={{ background: "#22262f", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8 }} />
                  <Bar dataKey="total" fill="#f43f5e" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : <p className="text-xs text-gray-500 text-center py-8">Sem dados no período</p>}
          </Card>

          {/* Income by category */}
          <Card>
            <h3 className="text-base font-semibold text-white mb-4">Fontes de Receita</h3>
            {stmt?.income_by_category && stmt.income_by_category.length > 0 ? (
              <ResponsiveContainer width="100%" height={320}>
                <BarChart data={stmt.income_by_category.slice(0, 8)} layout="vertical" margin={{ left: 90 }}>
                  <XAxis type="number" stroke="#6b7280" fontSize={11}
                    tickFormatter={(v) => `${(v/1000).toFixed(0)}k`} />
                  <YAxis type="category" dataKey="name" stroke="#6b7280" fontSize={11} width={85} />
                  <Tooltip formatter={(v: any) => formatCurrency(v as number)}
                    contentStyle={{ background: "#22262f", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8 }} />
                  <Bar dataKey="total" fill="#22c55e" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : <p className="text-xs text-gray-500 text-center py-8">Sem dados no período</p>}
          </Card>
        </div>

        {/* Trends */}
        <Card className="mt-6">
          <h3 className="text-base font-semibold text-white mb-4">Tendências de Categorias (6 meses)</h3>
          <div className="space-y-3">
            {trends?.slice(0, 10).map((t: any, i: number) => (
              <div key={i} className="flex items-center gap-4 p-3 rounded-lg" style={{ background: "var(--color-surface-2)" }}>
                <div className="w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0"
                  style={{ background: t.color + "20" }}>
                  <span className="w-3 h-3 rounded-full" style={{ background: t.color }} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-white">{t.name}</p>
                  <p className="text-xs text-gray-500">Média: {formatCurrency(t.avg_monthly)}/mês</p>
                </div>
                <Badge variant={t.growth_pct > 10 ? "danger" : t.growth_pct < -10 ? "success" : "neutral"}>
                  {t.growth_pct > 0 ? "+" : ""}{t.growth_pct}%
                </Badge>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </AppShell>
  );
}
