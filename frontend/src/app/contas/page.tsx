"use client";
import { useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { accountsApi } from "@/lib/api";
import { Card, Button, Input, Select, Modal, Badge, PageHeader, EmptyState } from "@/components/ui";
import { formatCurrency, ACCOUNT_TYPES } from "@/lib/utils";
import { Plus, Edit2, Trash2, Wallet, CreditCard, PiggyBank } from "lucide-react";
import toast from "react-hot-toast";

const COLORS = ["#22c55e", "#16a34a", "#0ea5e9", "#6366f1", "#8b5cf6", "#ec4899", "#f97316", "#eab308"];

export default function ContasPage() {
  const qc = useQueryClient();
  const [showModal, setShowModal] = useState(false);
  const [editing, setEditing] = useState<any>(null);

  const { data } = useQuery({ queryKey: ["accounts"], queryFn: () => accountsApi.list() });

  const deleteMut = useMutation({
    mutationFn: (id: string) => accountsApi.delete(id),
    onSuccess: () => {
      toast.success("Conta desativada");
      qc.invalidateQueries({ queryKey: ["accounts"] });
    },
  });

  return (
    <AppShell>
      <div className="p-8 max-w-[1200px] mx-auto">
        <PageHeader
          title="Contas"
          description="Gerencie suas contas bancárias, cartões e carteiras"
          actions={
            <Button leftIcon={<Plus size={14} />} onClick={() => { setEditing(null); setShowModal(true); }}>
              Nova conta
            </Button>
          }
        />

        {data?.accounts?.length === 0 ? (
          <EmptyState
            icon={<Wallet size={32} />}
            title="Nenhuma conta cadastrada"
            description="Adicione sua primeira conta para começar a organizar suas finanças"
            action={<Button onClick={() => setShowModal(true)} leftIcon={<Plus size={14} />}>Adicionar conta</Button>}
          />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {data?.accounts?.map((a: any) => (
              <Card key={a.id} className="relative overflow-hidden group">
                <div className="absolute -top-10 -right-10 w-32 h-32 rounded-full blur-3xl opacity-30"
                  style={{ background: a.color }} />
                <div className="relative">
                  <div className="flex items-start justify-between mb-4">
                    <div className="w-10 h-10 rounded-xl flex items-center justify-center"
                      style={{ background: a.color + "20", color: a.color }}>
                      {a.type === "cartao_credito" ? <CreditCard size={18} /> :
                       a.type === "poupanca" ? <PiggyBank size={18} /> : <Wallet size={18} />}
                    </div>
                    <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button onClick={() => { setEditing(a); setShowModal(true); }}
                        className="p-1.5 rounded-lg hover:bg-white/5">
                        <Edit2 size={12} className="text-gray-500" />
                      </button>
                      <button onClick={() => confirm("Desativar conta?") && deleteMut.mutate(a.id)}
                        className="p-1.5 rounded-lg hover:bg-rose-500/10">
                        <Trash2 size={12} className="text-rose-400" />
                      </button>
                    </div>
                  </div>
                  <p className="text-xs text-gray-500 mb-0.5">{a.bank_name || "—"}</p>
                  <p className="text-base font-semibold text-white mb-2">{a.name}</p>
                  <Badge>{ACCOUNT_TYPES.find(t => t.value === a.type)?.label || a.type}</Badge>
                  <div className="mt-4 pt-4 border-t" style={{ borderColor: "var(--color-border)" }}>
                    <p className="text-xs text-gray-500">Saldo</p>
                    <p className={`text-xl font-bold number-display ${a.balance >= 0 ? "text-income" : "text-expense"}`}>
                      {formatCurrency(a.balance)}
                    </p>
                    {a.credit_limit && (
                      <p className="text-xs text-gray-500 mt-1">
                        Limite: {formatCurrency(a.credit_limit)}
                      </p>
                    )}
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}

        {data?.accounts?.length > 0 && (
          <Card className="mt-6">
            <div className="flex items-center justify-between">
              <p className="text-sm text-gray-400">Saldo total consolidado</p>
              <p className="text-2xl font-bold text-white number-display">
                {formatCurrency(data.total_balance || 0)}
              </p>
            </div>
          </Card>
        )}

        {showModal && (
          <AccountModal editing={editing} onClose={() => { setShowModal(false); setEditing(null); }} />
        )}
      </div>
    </AppShell>
  );
}

function AccountModal({ editing, onClose }: any) {
  const qc = useQueryClient();
  const [form, setForm] = useState({
    name: editing?.name || "",
    type: editing?.type || "corrente",
    bank_name: editing?.bank_name || "",
    balance: editing?.balance || 0,
    credit_limit: editing?.credit_limit || "",
    closing_day: editing?.closing_day || "",
    due_day: editing?.due_day || "",
    color: editing?.color || COLORS[0],
  });

  const mut = useMutation({
    mutationFn: () => {
      const payload: any = {
        name: form.name,
        type: form.type,
        bank_name: form.bank_name || null,
        balance: parseFloat(String(form.balance)) || 0,
        color: form.color,
      };
      if (form.type === "cartao_credito") {
        if (form.credit_limit) payload.credit_limit = parseFloat(String(form.credit_limit));
        if (form.closing_day) payload.closing_day = parseInt(String(form.closing_day));
        if (form.due_day) payload.due_day = parseInt(String(form.due_day));
      }
      return editing
        ? accountsApi.update(editing.id, payload)
        : accountsApi.create(payload);
    },
    onSuccess: () => {
      toast.success(editing ? "Conta atualizada" : "Conta criada");
      qc.invalidateQueries({ queryKey: ["accounts"] });
      onClose();
    },
    onError: (e: any) => toast.error(e.response?.data?.detail || "Erro"),
  });

  return (
    <Modal open onClose={onClose} title={editing ? "Editar conta" : "Nova conta"}>
      <div className="space-y-4">
        <Input label="Nome" value={form.name}
          onChange={(e) => setForm({ ...form, name: e.target.value })}
          placeholder="Ex: Nubank, Itaú Corrente..." />
        <Select label="Tipo" value={form.type}
          onChange={(e) => setForm({ ...form, type: e.target.value })}
          options={ACCOUNT_TYPES} />
        <Input label="Banco" value={form.bank_name}
          onChange={(e) => setForm({ ...form, bank_name: e.target.value })}
          placeholder="Ex: Nubank, Itaú, Inter..." />
        <Input label="Saldo atual" type="number" step="0.01" value={form.balance}
          onChange={(e) => setForm({ ...form, balance: e.target.value as any })} />

        {form.type === "cartao_credito" && (
          <>
            <Input label="Limite" type="number" step="0.01" value={form.credit_limit}
              onChange={(e) => setForm({ ...form, credit_limit: e.target.value })} />
            <div className="grid grid-cols-2 gap-3">
              <Input label="Dia fechamento" type="number" min={1} max={31} value={form.closing_day}
                onChange={(e) => setForm({ ...form, closing_day: e.target.value })} />
              <Input label="Dia vencimento" type="number" min={1} max={31} value={form.due_day}
                onChange={(e) => setForm({ ...form, due_day: e.target.value })} />
            </div>
          </>
        )}

        <div>
          <label className="text-xs font-medium text-gray-400 mb-2 block">Cor</label>
          <div className="flex flex-wrap gap-2">
            {COLORS.map((c) => (
              <button key={c} type="button" onClick={() => setForm({ ...form, color: c })}
                className="w-9 h-9 rounded-xl transition-transform"
                style={{
                  background: c,
                  transform: form.color === c ? "scale(1.15)" : "scale(1)",
                  boxShadow: form.color === c ? `0 0 0 3px ${c}40` : "none",
                }}
              />
            ))}
          </div>
        </div>

        <div className="flex items-center justify-end gap-2 pt-2">
          <Button variant="ghost" onClick={onClose}>Cancelar</Button>
          <Button loading={mut.isPending} onClick={() => mut.mutate()} disabled={!form.name}>
            {editing ? "Salvar" : "Criar conta"}
          </Button>
        </div>
      </div>
    </Modal>
  );
}
