"use client";
import { useState } from "react";
import Link from "next/link";
import { Mail, ArrowLeft, Zap } from "lucide-react";
import { authApi } from "@/lib/api";
import { Button, Input } from "@/components/ui";
import toast from "react-hot-toast";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await authApi.forgotPassword(email);
      setSent(true);
    } catch (e: any) {
      toast.error("Erro ao enviar solicitação");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-8" style={{ background: "var(--color-surface)" }}>
      <div className="w-full max-w-md">
        <Link href="/auth/login" className="inline-flex items-center gap-2 text-sm text-gray-500 hover:text-white mb-6">
          <ArrowLeft size={14} /> Voltar para login
        </Link>
        <div className="flex items-center gap-3 mb-8">
          <div className="w-10 h-10 rounded-xl btn-brand flex items-center justify-center">
            <Zap size={18} className="text-white" />
          </div>
        </div>
        {sent ? (
          <div className="card p-8 text-center">
            <div className="w-12 h-12 rounded-full mx-auto mb-4 flex items-center justify-center" style={{ background: "rgba(34,197,94,0.15)" }}>
              <Mail size={20} style={{ color: "#22c55e" }} />
            </div>
            <h2 className="text-lg font-bold text-white mb-2">Confira seu e-mail</h2>
            <p className="text-sm text-gray-400">
              Se <span className="text-white">{email}</span> estiver cadastrado, enviaremos instruções para redefinir sua senha.
            </p>
          </div>
        ) : (
          <>
            <h1 className="text-2xl font-bold text-white mb-1">Recuperar senha</h1>
            <p className="text-sm text-gray-500 mb-8">Enviaremos um link para seu e-mail</p>
            <form onSubmit={handleSubmit} className="space-y-4">
              <Input label="E-mail" type="email" leftIcon={<Mail size={16} />}
                value={email} onChange={(e) => setEmail(e.target.value)} required />
              <Button type="submit" size="lg" loading={loading} className="w-full">
                Enviar link de recuperação
              </Button>
            </form>
          </>
        )}
      </div>
    </div>
  );
}
