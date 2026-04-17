"use client";
import { useState, useCallback } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { importsApi, accountsApi } from "@/lib/api";
import { Card, Button, Select, PageHeader, Badge, EmptyState } from "@/components/ui";
import { formatDate } from "@/lib/utils";
import { useDropzone } from "react-dropzone";
import { Upload, FileText, Image, File, CheckCircle2, XCircle, Clock, AlertCircle } from "lucide-react";
import toast from "react-hot-toast";

export default function ImportacoesPage() {
  const qc = useQueryClient();
  const { data: accounts } = useQuery({ queryKey: ["accounts"], queryFn: () => accountsApi.list() });
  const { data: history } = useQuery({ queryKey: ["imports"], queryFn: () => importsApi.history(), refetchInterval: 5000 });

  const [accountId, setAccountId] = useState("");
  const [uploadResult, setUploadResult] = useState<any>(null);

  const uploadMut = useMutation({
    mutationFn: (file: File) => importsApi.upload(file, accountId),
    onSuccess: (data) => {
      toast.success(`${data.imported} transações importadas!`);
      setUploadResult(data);
      qc.invalidateQueries({ queryKey: ["imports"] });
      qc.invalidateQueries({ queryKey: ["txns"] });
      qc.invalidateQueries({ queryKey: ["summary"] });
    },
    onError: (e: any) => toast.error(e.response?.data?.detail || "Erro ao importar"),
  });

  const onDrop = useCallback((files: File[]) => {
    if (!accountId) {
      toast.error("Selecione uma conta primeiro");
      return;
    }
    files.forEach((f) => uploadMut.mutate(f));
  }, [accountId]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/x-ofx": [".ofx"],
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx"],
      "application/pdf": [".pdf"],
      "image/*": [".png", ".jpg", ".jpeg", ".webp"],
    },
    maxSize: 50 * 1024 * 1024,
    disabled: !accountId || uploadMut.isPending,
  });

  return (
    <AppShell>
      <div className="p-8 max-w-[1400px] mx-auto">
        <PageHeader
          title="Importações"
          description="Importe extratos bancários em OFX, Excel, PDF ou prints de tela"
        />

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Upload area */}
          <div className="lg:col-span-2">
            <Card>
              <div className="mb-4">
                <label className="text-xs font-medium text-gray-400 mb-1.5 block">Conta destino</label>
                <select
                  value={accountId} onChange={(e) => setAccountId(e.target.value)}
                  className="w-full h-10 rounded-xl border text-sm text-white px-3"
                  style={{ background: "var(--color-surface-2)", borderColor: "var(--color-border)" }}
                >
                  <option value="">Selecione uma conta</option>
                  {accounts?.accounts?.map((a: any) => (
                    <option key={a.id} value={a.id}>{a.name} ({a.bank_name || a.type})</option>
                  ))}
                </select>
              </div>

              <div {...getRootProps()}
                className="border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-all"
                style={{
                  borderColor: isDragActive ? "#22c55e" : "var(--color-border)",
                  background: isDragActive ? "rgba(34,197,94,0.05)" : "transparent",
                  opacity: !accountId ? 0.5 : 1,
                }}
              >
                <input {...getInputProps()} />
                <div className="w-14 h-14 rounded-2xl mx-auto mb-4 flex items-center justify-center"
                  style={{ background: "rgba(34,197,94,0.1)" }}>
                  <Upload size={24} style={{ color: "#22c55e" }} />
                </div>
                <p className="text-base font-semibold text-white mb-2">
                  {isDragActive ? "Solte os arquivos aqui" : uploadMut.isPending ? "Processando..." : "Arraste arquivos ou clique para selecionar"}
                </p>
                <p className="text-xs text-gray-500">
                  OFX, XLSX, PDF ou imagens (prints) • até 50MB por arquivo
                </p>
                {uploadMut.isPending && (
                  <div className="mt-4 h-1 bg-white/5 rounded-full overflow-hidden">
                    <div className="h-full animate-pulse" style={{ background: "#22c55e", width: "60%" }} />
                  </div>
                )}
              </div>

              <div className="grid grid-cols-4 gap-3 mt-6">
                {[
                  { icon: <FileText size={18} />, label: "OFX", desc: "Extrato bancário" },
                  { icon: <File size={18} />, label: "XLSX", desc: "Planilha Excel" },
                  { icon: <FileText size={18} />, label: "PDF", desc: "Extrato em PDF" },
                  { icon: <Image size={18} />, label: "Imagem", desc: "Print (OCR)" },
                ].map((f, i) => (
                  <div key={i} className="p-3 rounded-xl text-center"
                    style={{ background: "var(--color-surface-2)", border: "1px solid var(--color-border)" }}>
                    <div className="text-gray-500 mb-2 flex justify-center">{f.icon}</div>
                    <p className="text-xs font-semibold text-white">{f.label}</p>
                    <p className="text-[10px] text-gray-600">{f.desc}</p>
                  </div>
                ))}
              </div>
            </Card>

            {/* Last upload preview */}
            {uploadResult?.preview && uploadResult.preview.length > 0 && (
              <Card className="mt-4">
                <h3 className="text-base font-semibold text-white mb-3">
                  Última importação: {uploadResult.imported} transações
                </h3>
                <div className="space-y-1.5 max-h-80 overflow-y-auto">
                  {uploadResult.preview.map((p: any, i: number) => (
                    <div key={i} className="flex items-center gap-3 p-2.5 rounded-lg hover:bg-white/5 text-sm">
                      <span className="text-xs text-gray-500 w-20 flex-shrink-0">{formatDate(p.date)}</span>
                      <span className="text-white flex-1 truncate">{p.description}</span>
                      {p.category ? (
                        <Badge variant="success">{p.category}</Badge>
                      ) : (
                        <Badge variant="warning">Sem categoria</Badge>
                      )}
                      <span className={`font-semibold number-display w-24 text-right ${p.type === "despesa" ? "text-expense" : "text-income"}`}>
                        {p.type === "despesa" ? "-" : "+"}R$ {p.amount.toFixed(2)}
                      </span>
                    </div>
                  ))}
                </div>
              </Card>
            )}
          </div>

          {/* History */}
          <div>
            <Card>
              <h3 className="text-base font-semibold text-white mb-4">Histórico</h3>
              <div className="space-y-2">
                {!history || history.length === 0 ? (
                  <EmptyState title="Sem importações" description="Faça seu primeiro upload" />
                ) : (
                  history.map((h: any) => (
                    <div key={h.id} className="p-3 rounded-lg" style={{ background: "var(--color-surface-2)" }}>
                      <div className="flex items-start gap-2 mb-1">
                        <StatusIcon status={h.status} />
                        <div className="flex-1 min-w-0">
                          <p className="text-sm text-white font-medium truncate">{h.filename}</p>
                          <p className="text-xs text-gray-500">{formatDate(h.created_at)}</p>
                        </div>
                      </div>
                      {h.status === "completed" && (
                        <div className="flex items-center gap-2 mt-2">
                          <Badge variant="success">{h.imported_transactions} importadas</Badge>
                          {h.duplicate_transactions > 0 && (
                            <Badge variant="warning">{h.duplicate_transactions} duplicadas</Badge>
                          )}
                        </div>
                      )}
                      {h.status === "failed" && h.error_message && (
                        <p className="text-xs text-rose-400 mt-1">{h.error_message}</p>
                      )}
                    </div>
                  ))
                )}
              </div>
            </Card>
          </div>
        </div>
      </div>
    </AppShell>
  );
}

function StatusIcon({ status }: { status: string }) {
  const map = {
    completed: <CheckCircle2 size={14} className="text-green-400" />,
    failed: <XCircle size={14} className="text-rose-400" />,
    processing: <Clock size={14} className="text-amber-400 animate-spin" />,
    pending: <AlertCircle size={14} className="text-gray-500" />,
  };
  return map[status as keyof typeof map] || map.pending;
}
