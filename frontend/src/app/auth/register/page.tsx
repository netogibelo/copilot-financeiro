"use client";
import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Mail, Lock, User, Zap } from "lucide-react";
import { authApi } from "@/lib/api";
import { useAuthStore } from "@/store/auth";
import { Button, Input } from "@/components/ui";
import toast from "react-hot-toast";

export default function RegisterPage() {
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();
  const { setTokens } = useAuthStore();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (form.password.length < 8) {
      toast.error("A senha deve ter pelo menos 8 caracteres");
      return;
    }
    setIsLoading(true);
    try {
      const data = await authApi.register(form.name, form.email, form.password);
      setTokens(data.access_token, data.refresh_token, data.user);
      toast.success("Conta criada com sucesso!");
      router.push("/dashboard");
    } catch (e: any) {
      toast.error(e.response?.data?.detail || "Erro ao criar conta");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-8" style={{ background: "var(--color-surface)" }}>
      <div className="w-full max-w-md">
        <Link href="/" className="flex items-center gap-3 mb-10 justify-center">
          <div className="w-10 h-10 rounded-xl btn-brand flex items-center justify-center">
            <Zap size={18} className="text-white" />
          </div>
          <div>
            <p className="text-lg font-bold text-white leading-tight">Copilot Financeiro</p>
          </div>
        </Link>
        <h1 className="text-2xl font-bold text-white mb-1 text-center">Crie sua conta grátis</h1>
        <p className="text-sm text-gray-500 mb-8 text-center">Leva menos de 1 minuto</p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <Input label="Nome completo" leftIcon={<User size={16} />}
            value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
          <Input label="E-mail" type="email" leftIcon={<Mail size={16} />}
            value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required />
          <Input label="Senha" type="password" leftIcon={<Lock size={16} />}
            placeholder="Mínimo 8 caracteres"
            value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} required />
          <Button type="submit" size="lg" loading={isLoading} className="w-full">
            Criar conta
          </Button>
        </form>

        <p className="text-center text-sm text-gray-500 mt-6">
          Já tem conta?{" "}
          <Link href="/auth/login" className="font-semibold" style={{ color: "#22c55e" }}>Fazer login</Link>
        </p>
      </div>
    </div>
  );
}
