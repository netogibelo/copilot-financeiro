"use client";
import { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Mail, Lock, Zap, TrendingUp, Sparkles, ShieldCheck } from "lucide-react";
import { useAuthStore } from "@/store/auth";
import { Button, Input } from "@/components/ui";
import toast from "react-hot-toast";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();
  const { login, loginWithGoogle, isAuthenticated } = useAuthStore();

  useEffect(() => {
    if (isAuthenticated) router.push("/dashboard");
  }, [isAuthenticated, router]);

  // Google OAuth
  useEffect(() => {
    const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;
    if (!clientId) return;
    const script = document.createElement("script");
    script.src = "https://accounts.google.com/gsi/client";
    script.async = true;
    script.defer = true;
    document.head.appendChild(script);
    script.onload = () => {
      // @ts-ignore
      window.google?.accounts.id.initialize({
        client_id: clientId,
        callback: async (response: any) => {
          try {
            await loginWithGoogle(response.credential);
            toast.success("Bem-vindo(a)!");
            router.push("/dashboard");
          } catch (e: any) {
            toast.error(e.response?.data?.detail || "Erro no login com Google");
          }
        },
      });
      // @ts-ignore
      window.google?.accounts.id.renderButton(document.getElementById("google-btn"), {
        theme: "filled_black", size: "large", width: 380, text: "continue_with", shape: "pill",
      });
    };
    return () => { script.remove(); };
  }, [loginWithGoogle, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    try {
      await login(email, password);
      toast.success("Bem-vindo(a)!");
      router.push("/dashboard");
    } catch (e: any) {
      toast.error(e.response?.data?.detail || "Erro ao fazer login");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex">
      {/* Left - Form */}
      <div className="flex-1 flex items-center justify-center p-8" style={{ background: "var(--color-surface)" }}>
        <div className="w-full max-w-md">
          <Link href="/" className="flex items-center gap-3 mb-10">
            <div className="w-10 h-10 rounded-xl btn-brand flex items-center justify-center">
              <Zap size={18} className="text-white" />
            </div>
            <div>
              <p className="text-lg font-bold text-white leading-tight">Copilot Financeiro</p>
              <p className="text-xs text-gray-500">Sua vida financeira inteligente</p>
            </div>
          </Link>

          <h1 className="text-2xl font-bold text-white mb-1">Bem-vindo de volta</h1>
          <p className="text-sm text-gray-500 mb-8">Entre para acessar sua conta</p>

          <form onSubmit={handleSubmit} className="space-y-4">
            <Input
              label="E-mail" type="email" placeholder="voce@email.com"
              leftIcon={<Mail size={16} />} value={email}
              onChange={(e) => setEmail(e.target.value)} required
            />
            <Input
              label="Senha" type="password" placeholder="••••••••"
              leftIcon={<Lock size={16} />} value={password}
              onChange={(e) => setPassword(e.target.value)} required
            />
            <div className="flex items-center justify-between pt-2">
              <label className="flex items-center gap-2 text-xs text-gray-500 cursor-pointer">
                <input type="checkbox" className="w-3.5 h-3.5 rounded" />
                Lembrar de mim
              </label>
              <Link href="/auth/forgot-password" className="text-xs text-brand-400 hover:underline" style={{ color: "#22c55e" }}>
                Esqueceu a senha?
              </Link>
            </div>
            <Button type="submit" size="lg" loading={isLoading} className="w-full">
              Entrar
            </Button>
          </form>

          <div className="flex items-center gap-3 my-6">
            <div className="flex-1 h-px bg-white/10" />
            <span className="text-xs text-gray-600">ou continue com</span>
            <div className="flex-1 h-px bg-white/10" />
          </div>

          <div id="google-btn" className="flex justify-center" />

          <p className="text-center text-sm text-gray-500 mt-8">
            Não tem conta?{" "}
            <Link href="/auth/register" className="font-semibold hover:underline" style={{ color: "#22c55e" }}>
              Cadastre-se grátis
            </Link>
          </p>
        </div>
      </div>

      {/* Right - Brand showcase */}
      <div className="hidden lg:flex flex-1 relative overflow-hidden" style={{ background: "linear-gradient(135deg, #052e16 0%, #14532d 50%, #166534 100%)" }}>
        <div className="absolute inset-0 bg-mesh-green opacity-40" />
        <div className="absolute top-1/4 -right-20 w-80 h-80 rounded-full blur-3xl" style={{ background: "rgba(34, 197, 94, 0.2)" }} />
        <div className="absolute bottom-1/4 -left-20 w-80 h-80 rounded-full blur-3xl" style={{ background: "rgba(16, 185, 129, 0.15)" }} />

        <div className="relative z-10 flex flex-col justify-center p-16 max-w-xl">
          <div className="mb-8">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full mb-6 backdrop-blur-md" style={{ background: "rgba(34, 197, 94, 0.15)", border: "1px solid rgba(34, 197, 94, 0.3)" }}>
              <Sparkles size={12} className="text-green-300" />
              <span className="text-xs font-medium text-green-300">Potencializado por IA</span>
            </div>
            <h2 className="text-5xl font-bold text-white leading-[1.1] mb-6 font-display">
              Sua vida financeira,<br />
              <span className="bg-gradient-to-r from-green-300 to-emerald-400 bg-clip-text text-transparent">
                sob controle total.
              </span>
            </h2>
            <p className="text-green-100/80 text-lg leading-relaxed">
              Organize suas finanças, preveja saldos futuros e deixe a IA detectar padrões, assinaturas e oportunidades de economia.
            </p>
          </div>

          <div className="space-y-4 mt-8">
            {[
              { icon: <TrendingUp size={18} />, title: "Previsão inteligente de saldo", text: "Saiba como seu dinheiro vai estar daqui a 3 meses." },
              { icon: <Sparkles size={18} />, title: "Categorização automática", text: "IA aprende com seus gastos e categoriza sozinha." },
              { icon: <ShieldCheck size={18} />, title: "Seguro e criptografado", text: "Seus dados protegidos com padrões bancários." },
            ].map((f, i) => (
              <div key={i} className="flex items-start gap-4 p-4 rounded-xl backdrop-blur-md" style={{ background: "rgba(255, 255, 255, 0.05)", border: "1px solid rgba(255, 255, 255, 0.1)" }}>
                <div className="w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0" style={{ background: "rgba(34, 197, 94, 0.25)" }}>
                  <span className="text-green-300">{f.icon}</span>
                </div>
                <div>
                  <p className="font-semibold text-white text-sm mb-0.5">{f.title}</p>
                  <p className="text-xs text-green-100/70">{f.text}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
