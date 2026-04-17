"use client";
import { useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { categoriesApi } from "@/lib/api";
import { Card, Button, Input, Select, Modal, Badge, PageHeader, EmptyState } from "@/components/ui";
import { Plus, Edit2, Trash2, Tag } from "lucide-react";
import toast from "react-hot-toast";
import * as Tabs from "@radix-ui/react-tabs";

const COLORS = ["#22c55e", "#16a34a", "#ef4444", "#f59e0b", "#8b5cf6", "#3b82f6", "#ec4899", "#14b8a6", "#f97316", "#6366f1"];

export default function CategoriasPage() {
  const qc = useQueryClient();
  const [activeTab, setActiveTab] = useState("despesa");
  const [showModal, setShowModal] = useState(false);
  const [editing, setEditing] = useState<any>(null);

  const { data: categories } = useQuery({
    queryKey: ["categories", activeTab],
    queryFn: () => categoriesApi.list(activeTab),
  });

  const deleteMut = useMutation({
    mutationFn: (id: string) => categoriesApi.delete(id),
    onSuccess: () => {
      toast.success("Categoria excluída");
      qc.invalidateQueries({ queryKey: ["categories"] });
    },
    onError: (e: any) => toast.error(e.response?.data?.detail || "Erro"),
  });

  return (
    <AppShell>
      <div className="p-8 max-w-[1200px] mx-auto">
        <PageHeader
          title="Categorias"
          description="Gerencie categorias para organizar seus lançamentos"
          actions={
            <Button leftIcon={<Plus size={14} />} onClick={() => { setEditing(null); setShowModal(true); }}>
              Nova categoria
            </Button>
          }
        />

        <Tabs.Root value={activeTab} onValueChange={setActiveTab}>
          <Tabs.List className="flex gap-1 p-1 rounded-xl mb-6 w-fit" style={{ background: "var(--color-surface-1)", border: "1px solid var(--color-border)" }}>
            {["despesa", "receita", "investimento", "transferencia"].map((t) => (
              <Tabs.Trigger key={t} value={t}
                className="px-4 py-2 rounded-lg text-sm font-medium text-gray-400 data-[state=active]:text-white transition-colors capitalize"
                style={activeTab === t ? { background: "rgba(34,197,94,0.15)", color: "#22c55e" } : {}}
              >
                {t === "despesa" ? "Despesas" : t === "receita" ? "Receitas" : t === "investimento" ? "Investimentos" : "Transferências"}
              </Tabs.Trigger>
            ))}
          </Tabs.List>

          <Tabs.Content value={activeTab}>
            {!categories || categories.length === 0 ? (
              <EmptyState
                icon={<Tag size={32} />}
                title="Nenhuma categoria"
                description="Adicione sua primeira categoria"
                action={<Button onClick={() => setShowModal(true)} leftIcon={<Plus size={14} />}>Nova categoria</Button>}
              />
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
                {categories.map((c: any) => (
                  <Card key={c.id} className="relative group">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0"
                        style={{ background: c.color + "20", color: c.color }}>
                        <Tag size={16} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-semibold text-white truncate">{c.name}</p>
                        <div className="flex items-center gap-1 mt-1">
                          {c.is_system && <Badge variant="info">Sistema</Badge>}
                          {!c.is_system && <Badge variant="success">Personalizada</Badge>}
                        </div>
                      </div>
                      {!c.is_system && (
                        <div className="flex flex-col gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                          <button onClick={() => { setEditing(c); setShowModal(true); }}
                            className="p-1 rounded hover:bg-white/5">
                            <Edit2 size={12} className="text-gray-500" />
                          </button>
                          <button onClick={() => confirm("Excluir?") && deleteMut.mutate(c.id)}
                            className="p-1 rounded hover:bg-rose-500/10">
                            <Trash2 size={12} className="text-rose-400" />
                          </button>
                        </div>
                      )}
                    </div>
                  </Card>
                ))}
              </div>
            )}
          </Tabs.Content>
        </Tabs.Root>

        {showModal && (
          <CategoryModal type={activeTab} editing={editing}
            onClose={() => { setShowModal(false); setEditing(null); }} />
        )}
      </div>
    </AppShell>
  );
}

function CategoryModal({ type, editing, onClose }: any) {
  const qc = useQueryClient();
  const [form, setForm] = useState({
    name: editing?.name || "",
    color: editing?.color || COLORS[0],
    icon: editing?.icon || "tag",
  });

  const mut = useMutation({
    mutationFn: () => editing
      ? categoriesApi.update(editing.id, form)
      : categoriesApi.create({ ...form, type }),
    onSuccess: () => {
      toast.success(editing ? "Categoria atualizada" : "Categoria criada");
      qc.invalidateQueries({ queryKey: ["categories"] });
      onClose();
    },
    onError: (e: any) => toast.error(e.response?.data?.detail || "Erro"),
  });

  return (
    <Modal open onClose={onClose} title={editing ? "Editar categoria" : "Nova categoria"}>
      <div className="space-y-4">
        <Input label="Nome" value={form.name}
          onChange={(e) => setForm({ ...form, name: e.target.value })}
          placeholder="Ex: Academia" />

        <div>
          <label className="text-xs font-medium text-gray-400 mb-2 block">Cor</label>
          <div className="flex flex-wrap gap-2">
            {COLORS.map((c) => (
              <button key={c} onClick={() => setForm({ ...form, color: c })}
                className="w-9 h-9 rounded-xl transition-all"
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
            {editing ? "Salvar" : "Criar categoria"}
          </Button>
        </div>
      </div>
    </Modal>
  );
}
