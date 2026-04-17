"use client";
import { useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import * as Tabs from "@radix-ui/react-tabs";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { transactionsApi, accountsApi, categoriesApi, analyticsApi } from "@/lib/api";
import { Card, Button, Input, Select, Textarea, Modal, Badge, EmptyState, PageHeader, Spinner } from "@/components/ui";
import { formatCurrency, formatDate, currentMonthYear, typeClass, typeLabel, TRANSACTION_TYPES } from "@/lib/utils";
import { Plus, Search, Trash2, Edit2, ArrowUpRight, ArrowDownRight, Repeat2, Filter, Calendar, TrendingUp, TrendingDown } from "lucide-react";
import toast from "react-hot-toast";
import { LineChart, Line, AreaChart, Area, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

export default function FinanceiroPage() {
  const [activeTab, setActiveTab] = useState("recebimentos");
  const { month, year } = currentMonthYear();

  return (
    <AppShell>
      <div className="p-8 max-w-[1600px] mx-auto">
        <PageHeader
          title="Financeiro"
          description="Gerencie recebimentos, pagamentos, fluxo de caixa e resultados"
        />

        <Tabs.Root value={activeTab} onValueChange={setActiveTab}>
          <Tabs.List className="flex gap-1 p-1 rounded-xl mb-6 w-fit" style={{ background: "var(--color-surface-1)", border: "1px solid var(--color-border)" }}>
            {[
              { value: "recebimentos", label: "Recebimentos", icon: ArrowUpRight },
              { value: "pagamentos", label: "Pagamentos", icon: ArrowDownRight },
              { value: "fluxo", label: "Fluxo de Caixa", icon: TrendingUp },
              { value: "resultados", label: "Resultados", icon: TrendingDown },
            ].map(({ value, label, icon: Icon }) => (
              <Tabs.Trigger key={value} value={value}
                className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-gray-400 data-[state=active]:text-white data-[state=active]:bg-brand-500/15 transition-colors"
                style={{ ...(activeTab === value && { background: "rgba(34,197,94,0.15)", color: "#22c55e" }) }}
              >
                <Icon size={14} /> {label}
              </Tabs.Trigger>
            ))}
          </Tabs.List>

          <Tabs.Content value="recebimentos">
            <TransactionList type="receita" />
          </Tabs.Content>
          <Tabs.Content value="pagamentos">
            <TransactionList type="despesa" />
          </Tabs.Content>
          <Tabs.Content value="fluxo">
            <CashflowView />
          </Tabs.Content>
          <Tabs.Content value="resultados">
            <ResultsView />
          </Tabs.Content>
        </Tabs.Root>
      </div>
    </AppShell>
  );
}

function TransactionList({ type }: { type: "receita" | "despesa" }) {
  const qc = useQueryClient();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [accountFilter, setAccountFilter] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [showModal, setShowModal] = useState(false);
  const [editing, setEditing] = useState<any>(null);

  const { data: txns, isLoading } = useQuery({
    queryKey: ["txns", type, page, search, accountFilter, categoryFilter],
    queryFn: () => transactionsApi.list({
      type, page, per_page: 20,
      search: search || undefined,
      account_id: accountFilter || undefined,
      category_id: categoryFilter || undefined,
    }),
  });

  const { data: accounts } = useQuery({ queryKey: ["accounts"], queryFn: () => accountsApi.list() });
  const { data: categories } = useQuery({ queryKey: ["cats", type], queryFn: () => categoriesApi.list(type) });

  const deleteMut = useMutation({
    mutationFn: (id: string) => transactionsApi.delete(id),
    onSuccess: () => {
      toast.success("Lançamento excluído");
      qc.invalidateQueries({ queryKey: ["txns"] });
    },
  });

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[200px] max-w-md">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
          <input
            placeholder="Buscar lançamento..."
            value={search} onChange={(e) => setSearch(e.target.value)}
            className="w-full h-10 rounded-xl border text-sm text-white placeholder-gray-600 pl-10 pr-3 focus:outline-none focus:border-brand-500/40"
            style={{ background: "var(--color-surface-2)", borderColor: "var(--color-border)" }}
          />
        </div>
        <select
          value={accountFilter} onChange={(e) => setAccountFilter(e.target.value)}
          className="h-10 rounded-xl border text-sm text-white px-3"
          style={{ background: "var(--color-surface-2)", borderColor: "var(--color-border)" }}
        >
          <option value="">Todas as contas</option>
          {accounts?.accounts?.map((a: any) => (
            <option key={a.id} value={a.id}>{a.name}</option>
          ))}
        </select>
        <select
          value={categoryFilter} onChange={(e) => setCategoryFilter(e.target.value)}
          className="h-10 rounded-xl border text-sm text-white px-3"
          style={{ background: "var(--color-surface-2)", borderColor: "var(--color-border)" }}
        >
          <option value="">Todas as categorias</option>
          {categories?.map((c: any) => (
            <option key={c.id} value={c.id}>{c.name}</option>
          ))}
        </select>
        <Button leftIcon={<Plus size={14} />} onClick={() => { setEditing(null); setShowModal(true); }}>
          Novo {type === "receita" ? "recebimento" : "pagamento"}
        </Button>
      </div>

      {/* Table */}
      <Card className="p-0 overflow-hidden">
        {isLoading ? (
          <div className="p-12 flex justify-center"><Spinner /></div>
        ) : !txns?.data || txns.data.length === 0 ? (
          <EmptyState
            title="Nenhum lançamento encontrado"
            description={`Adicione seu primeiro ${type === "receita" ? "recebimento" : "pagamento"} para começar`}
            action={<Button onClick={() => setShowModal(true)} leftIcon={<Plus size={14} />}>Adicionar</Button>}
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b" style={{ borderColor: "var(--color-border)" }}>
                  <th className="text-left p-3 font-medium text-gray-500 text-xs uppercase">Data</th>
                  <th className="text-left p-3 font-medium text-gray-500 text-xs uppercase">Descrição</th>
                  <th className="text-left p-3 font-medium text-gray-500 text-xs uppercase">Categoria</th>
                  <th className="text-left p-3 font-medium text-gray-500 text-xs uppercase">Conta</th>
                  <th className="text-right p-3 font-medium text-gray-500 text-xs uppercase">Valor</th>
                  <th className="p-3 w-20"></th>
                </tr>
              </thead>
              <tbody>
                {txns.data.map((t: any) => (
                  <tr key={t.id} className="border-b hover:bg-white/[0.02] transition-colors" style={{ borderColor: "var(--color-border)" }}>
                    <td className="p-3 text-gray-400">{formatDate(t.date)}</td>
                    <td className="p-3">
                      <div>
                        <p className="text-white font-medium">{t.description}</p>
                        {t.installment_current && t.installment_total && (
                          <Badge variant="purple" className="mt-1">
                            <Repeat2 size={10} className="mr-1" />
                            {t.installment_current}/{t.installment_total}
                          </Badge>
                        )}
                      </div>
                    </td>
                    <td className="p-3">
                      {t.category_name ? (
                        <div className="flex items-center gap-2">
                          <span className="w-2 h-2 rounded-full" style={{ background: t.category_color || "#6b7280" }} />
                          <span className="text-gray-300">{t.category_name}</span>
                        </div>
                      ) : (
                        <Badge variant="warning">Sem categoria</Badge>
                      )}
                    </td>
                    <td className="p-3 text-gray-400">{t.account_name}</td>
                    <td className={`p-3 text-right font-semibold number-display ${typeClass(t.type)}`}>
                      {t.type === "despesa" ? "-" : "+"}{formatCurrency(t.amount)}
                    </td>
                    <td className="p-3">
                      <div className="flex items-center justify-end gap-1">
                        <button onClick={() => { setEditing(t); setShowModal(true); }}
                          className="p-1.5 rounded-lg hover:bg-white/5 transition-colors">
                          <Edit2 size={12} className="text-gray-500" />
                        </button>
                        <button onClick={() => confirm("Excluir este lançamento?") && deleteMut.mutate(t.id)}
                          className="p-1.5 rounded-lg hover:bg-rose-500/10 transition-colors">
                          <Trash2 size={12} className="text-rose-400" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {txns?.total > 20 && (
          <div className="flex items-center justify-between p-4 border-t" style={{ borderColor: "var(--color-border)" }}>
            <p className="text-xs text-gray-500">
              {(page - 1) * 20 + 1} - {Math.min(page * 20, txns.total)} de {txns.total}
            </p>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={() => setPage(Math.max(1, page - 1))} disabled={page === 1}>Anterior</Button>
              <Button variant="outline" size="sm" onClick={() => setPage(page + 1)} disabled={page >= txns.pages}>Próxima</Button>
            </div>
          </div>
        )}
      </Card>

      {/* Modal */}
      {showModal && (
        <TransactionModal
          type={type}
          editing={editing}
          onClose={() => { setShowModal(false); setEditing(null); }}
          accounts={accounts?.accounts || []}
          categories={categories || []}
        />
      )}
    </div>
  );
}

function TransactionModal({ type, editing, onClose, accounts, categories }: any) {
  const qc = useQueryClient();
  const [form, setForm] = useState({
    description: editing?.description || "",
    amount: editing?.amount || "",
    date: editing?.date || new Date().toISOString().split("T")[0],
    account_id: editing?.account_id || (accounts[0]?.id || ""),
    category_id: editing?.category_id || "",
    notes: editing?.notes || "",
    installment_total: editing?.installment_total || "",
  });

  const mut = useMutation({
    mutationFn: async () => {
      const payload = {
        type,
        description: form.description,
        amount: parseFloat(form.amount),
        date: form.date,
        account_id: form.account_id,
        category_id: form.category_id || undefined,
        notes: form.notes || undefined,
        installment_total: form.installment_total ? parseInt(form.installment_total) : undefined,
        installment_current: form.installment_total ? 1 : undefined,
      };
      return editing
        ? transactionsApi.update(editing.id, payload)
        : transactionsApi.create(payload);
    },
    onSuccess: () => {
      toast.success(editing ? "Lançamento atualizado" : "Lançamento criado");
      qc.invalidateQueries({ queryKey: ["txns"] });
      qc.invalidateQueries({ queryKey: ["summary"] });
      onClose();
    },
    onError: (e: any) => toast.error(e.response?.data?.detail || "Erro"),
  });

  // Auto-suggest category
  const suggestCategory = async () => {
    if (!form.description) return;
    const s = await transactionsApi.suggestCategory(form.description);
    if (s.category_id) {
      setForm((f) => ({ ...f, category_id: s.category_id }));
      toast.success(`💡 Categoria sugerida: ${s.category_name}`);
    }
  };

  return (
    <Modal open onClose={onClose} title={editing ? "Editar lançamento" : `Novo ${type === "receita" ? "recebimento" : "pagamento"}`}>
      <div className="space-y-4">
        <Input label="Descrição" value={form.description}
          onChange={(e) => setForm({ ...form, description: e.target.value })}
          onBlur={suggestCategory}
          placeholder="Ex: Supermercado Carrefour"
        />
        <div className="grid grid-cols-2 gap-3">
          <Input label="Valor" type="number" step="0.01" value={form.amount}
            onChange={(e) => setForm({ ...form, amount: e.target.value })} placeholder="0,00" />
          <Input label="Data" type="date" value={form.date}
            onChange={(e) => setForm({ ...form, date: e.target.value })} />
        </div>
        <Select label="Conta" value={form.account_id}
          onChange={(e) => setForm({ ...form, account_id: e.target.value })}
          options={accounts.map((a: any) => ({ value: a.id, label: a.name }))} />
        <Select label="Categoria" value={form.category_id}
          onChange={(e) => setForm({ ...form, category_id: e.target.value })}
          options={categories.map((c: any) => ({ value: c.id, label: c.name }))} />
        {type === "despesa" && (
          <Input label="Parcelas (opcional)" type="number" min={1} max={60}
            value={form.installment_total} placeholder="Ex: 12"
            onChange={(e) => setForm({ ...form, installment_total: e.target.value })} />
        )}
        <Textarea label="Observações" value={form.notes} rows={2}
          onChange={(e) => setForm({ ...form, notes: e.target.value })} />

        <div className="flex items-center justify-end gap-2 pt-2">
          <Button variant="ghost" onClick={onClose}>Cancelar</Button>
          <Button loading={mut.isPending} onClick={() => mut.mutate()} disabled={!form.description || !form.amount || !form.account_id}>
            {editing ? "Salvar alterações" : "Criar lançamento"}
          </Button>
        </div>
      </div>
    </Modal>
  );
}

function CashflowView() {
  const { data: monthly } = useQuery({ queryKey: ["monthly-full"], queryFn: () => analyticsApi.monthlyComparison(12) });

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <Card>
        <h3 className="text-base font-semibold text-white mb-4">Receitas vs Despesas (12 meses)</h3>
        <ResponsiveContainer width="100%" height={320}>
          <BarChart data={monthly || []}>
            <XAxis dataKey="label" stroke="#6b7280" fontSize={11} />
            <YAxis stroke="#6b7280" fontSize={11} tickFormatter={(v) => `${(v/1000).toFixed(0)}k`} />
            <Tooltip formatter={(v: any) => formatCurrency(v as number)}
              contentStyle={{ background: "#22262f", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8 }} />
            <Bar dataKey="income" fill="#22c55e" name="Receita" radius={[4, 4, 0, 0]} />
            <Bar dataKey="expense" fill="#f43f5e" name="Despesa" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </Card>

      <Card>
        <h3 className="text-base font-semibold text-white mb-4">Saldo Mensal</h3>
        <ResponsiveContainer width="100%" height={320}>
          <AreaChart data={monthly || []}>
            <defs>
              <linearGradient id="gBal" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#22c55e" stopOpacity={0.4} />
                <stop offset="100%" stopColor="#22c55e" stopOpacity={0} />
              </linearGradient>
            </defs>
            <XAxis dataKey="label" stroke="#6b7280" fontSize={11} />
            <YAxis stroke="#6b7280" fontSize={11} />
            <Tooltip formatter={(v: any) => formatCurrency(v as number)}
              contentStyle={{ background: "#22262f", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8 }} />
            <Area type="monotone" dataKey="balance" stroke="#22c55e" fill="url(#gBal)" strokeWidth={2} name="Saldo" />
          </AreaChart>
        </ResponsiveContainer>
      </Card>
    </div>
  );
}

function ResultsView() {
  const { data: monthly } = useQuery({ queryKey: ["monthly-results"], queryFn: () => analyticsApi.monthlyComparison(6) });

  const totalIncome = monthly?.reduce((acc: number, m: any) => acc + m.income, 0) || 0;
  const totalExpense = monthly?.reduce((acc: number, m: any) => acc + m.expense, 0) || 0;
  const totalInvestment = monthly?.reduce((acc: number, m: any) => acc + m.investment, 0) || 0;
  const netResult = totalIncome - totalExpense - totalInvestment;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <p className="text-xs text-gray-500 mb-1">Total Receitas (6 meses)</p>
          <p className="text-xl font-bold text-income number-display">{formatCurrency(totalIncome)}</p>
        </Card>
        <Card>
          <p className="text-xs text-gray-500 mb-1">Total Despesas</p>
          <p className="text-xl font-bold text-expense number-display">{formatCurrency(totalExpense)}</p>
        </Card>
        <Card>
          <p className="text-xs text-gray-500 mb-1">Total Investido</p>
          <p className="text-xl font-bold text-investment number-display">{formatCurrency(totalInvestment)}</p>
        </Card>
        <Card>
          <p className="text-xs text-gray-500 mb-1">Resultado Líquido</p>
          <p className={`text-xl font-bold number-display ${netResult >= 0 ? "text-income" : "text-expense"}`}>
            {formatCurrency(netResult)}
          </p>
        </Card>
      </div>

      <Card>
        <h3 className="text-base font-semibold text-white mb-4">Detalhamento mensal</h3>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-xs uppercase text-gray-500" style={{ borderColor: "var(--color-border)" }}>
              <th className="text-left p-3">Mês</th>
              <th className="text-right p-3">Receitas</th>
              <th className="text-right p-3">Despesas</th>
              <th className="text-right p-3">Investimentos</th>
              <th className="text-right p-3">Saldo</th>
            </tr>
          </thead>
          <tbody>
            {monthly?.map((m: any, i: number) => (
              <tr key={i} className="border-b" style={{ borderColor: "var(--color-border)" }}>
                <td className="p-3 text-white font-medium">{m.label}</td>
                <td className="p-3 text-right text-income number-display">{formatCurrency(m.income)}</td>
                <td className="p-3 text-right text-expense number-display">{formatCurrency(m.expense)}</td>
                <td className="p-3 text-right text-investment number-display">{formatCurrency(m.investment)}</td>
                <td className={`p-3 text-right font-semibold number-display ${m.balance >= 0 ? "text-income" : "text-expense"}`}>
                  {formatCurrency(m.balance)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
