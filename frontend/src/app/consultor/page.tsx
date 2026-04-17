"use client";
import { useState, useRef, useEffect } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { useMutation, useQuery } from "@tanstack/react-query";
import { aiApi } from "@/lib/api";
import { Card, Button, PageHeader } from "@/components/ui";
import { Send, Sparkles, Bot, User, MessageSquare, TrendingDown, PiggyBank, Calendar, ArrowRight } from "lucide-react";
import toast from "react-hot-toast";

const SUGGESTED_PROMPTS = [
  { icon: TrendingDown, text: "Onde estou gastando mais este mês?" },
  { icon: PiggyBank, text: "Quais assinaturas posso cancelar?" },
  { icon: Calendar, text: "Qual será meu saldo daqui a 3 meses?" },
  { icon: Sparkles, text: "Como posso economizar R$ 500 por mês?" },
];

interface Message {
  role: "user" | "assistant";
  content: string;
  timestamp?: Date;
}

export default function ConsultorPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [conversationId, setConversationId] = useState<string | undefined>();
  const endRef = useRef<HTMLDivElement>(null);

  const { data: conversations } = useQuery({
    queryKey: ["conversations"],
    queryFn: () => aiApi.conversations(),
  });

  const chatMut = useMutation({
    mutationFn: (msg: string) => aiApi.chat(msg, conversationId),
    onSuccess: (data) => {
      setConversationId(data.conversation_id);
      setMessages((prev) => [...prev, { role: "assistant", content: data.response, timestamp: new Date() }]);
    },
    onError: () => toast.error("Erro ao comunicar com o consultor"),
  });

  const send = (text?: string) => {
    const msg = text || input.trim();
    if (!msg) return;
    setMessages((prev) => [...prev, { role: "user", content: msg, timestamp: new Date() }]);
    setInput("");
    chatMut.mutate(msg);
  };

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const loadConversation = async (id: string) => {
    const conv = await aiApi.getConversation(id);
    setMessages(conv.messages || []);
    setConversationId(id);
  };

  return (
    <AppShell>
      <div className="p-8 max-w-[1400px] mx-auto">
        <PageHeader
          title="Consultor Financeiro IA"
          description="Seu assistente pessoal com acesso a todos os seus dados financeiros"
        />

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 h-[calc(100vh-200px)]">
          {/* Sidebar - conversations */}
          <Card className="lg:col-span-1 p-4 overflow-y-auto">
            <Button className="w-full mb-4" leftIcon={<Sparkles size={14} />}
              onClick={() => { setMessages([]); setConversationId(undefined); }}>
              Nova conversa
            </Button>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Histórico</p>
            <div className="space-y-1">
              {conversations?.length ? conversations.map((c: any) => (
                <button key={c.id} onClick={() => loadConversation(c.id)}
                  className="w-full text-left p-2 rounded-lg hover:bg-white/5 transition-colors">
                  <p className="text-sm text-white truncate">{c.title}</p>
                  <p className="text-xs text-gray-600">{c.message_count} mensagens</p>
                </button>
              )) : (
                <p className="text-xs text-gray-600 p-2">Sem conversas ainda</p>
              )}
            </div>
          </Card>

          {/* Chat area */}
          <div className="lg:col-span-3 flex flex-col">
            <Card className="flex-1 flex flex-col overflow-hidden p-0">
              {/* Messages */}
              <div className="flex-1 overflow-y-auto p-6 space-y-4">
                {messages.length === 0 ? (
                  <div className="flex flex-col items-center justify-center h-full text-center">
                    <div className="w-16 h-16 rounded-2xl flex items-center justify-center mb-4"
                      style={{ background: "linear-gradient(135deg, #22c55e, #15803d)", boxShadow: "0 0 40px rgba(34,197,94,0.3)" }}>
                      <Bot size={28} className="text-white" />
                    </div>
                    <h2 className="text-2xl font-bold text-white mb-2">Olá! Sou seu Copilot 👋</h2>
                    <p className="text-sm text-gray-500 max-w-md mb-8">
                      Tenho acesso aos seus dados financeiros e posso ajudar com análises, previsões e recomendações personalizadas.
                    </p>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-w-2xl w-full">
                      {SUGGESTED_PROMPTS.map((p, i) => (
                        <button key={i} onClick={() => send(p.text)}
                          className="flex items-center gap-3 p-4 rounded-xl text-left transition-all hover:border-brand-500/30"
                          style={{ background: "var(--color-surface-2)", border: "1px solid var(--color-border)" }}>
                          <div className="w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0"
                            style={{ background: "rgba(34,197,94,0.15)", color: "#22c55e" }}>
                            <p.icon size={14} />
                          </div>
                          <span className="text-sm text-gray-200 flex-1">{p.text}</span>
                          <ArrowRight size={14} className="text-gray-600" />
                        </button>
                      ))}
                    </div>
                  </div>
                ) : (
                  messages.map((m, i) => (
                    <div key={i} className={`flex gap-3 animate-fade-up ${m.role === "user" ? "flex-row-reverse" : ""}`}>
                      <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
                        style={{
                          background: m.role === "user" ? "var(--color-surface-2)" : "linear-gradient(135deg, #22c55e, #15803d)",
                        }}>
                        {m.role === "user" ? <User size={14} className="text-gray-400" /> : <Bot size={14} className="text-white" />}
                      </div>
                      <div className={`max-w-[75%] p-4 rounded-2xl ${m.role === "user" ? "rounded-tr-sm" : "rounded-tl-sm"}`}
                        style={{
                          background: m.role === "user" ? "rgba(34,197,94,0.1)" : "var(--color-surface-2)",
                          border: m.role === "user" ? "1px solid rgba(34,197,94,0.2)" : "1px solid var(--color-border)",
                        }}>
                        <p className="text-sm text-gray-100 whitespace-pre-wrap leading-relaxed">{m.content}</p>
                      </div>
                    </div>
                  ))
                )}
                {chatMut.isPending && (
                  <div className="flex gap-3">
                    <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
                      style={{ background: "linear-gradient(135deg, #22c55e, #15803d)" }}>
                      <Bot size={14} className="text-white" />
                    </div>
                    <div className="p-4 rounded-2xl rounded-tl-sm flex gap-1.5"
                      style={{ background: "var(--color-surface-2)", border: "1px solid var(--color-border)" }}>
                      <span className="w-2 h-2 rounded-full animate-pulse" style={{ background: "#22c55e" }} />
                      <span className="w-2 h-2 rounded-full animate-pulse" style={{ background: "#22c55e", animationDelay: "0.2s" }} />
                      <span className="w-2 h-2 rounded-full animate-pulse" style={{ background: "#22c55e", animationDelay: "0.4s" }} />
                    </div>
                  </div>
                )}
                <div ref={endRef} />
              </div>

              {/* Input */}
              <div className="p-4 border-t" style={{ borderColor: "var(--color-border)" }}>
                <div className="flex gap-2">
                  <input
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && send()}
                    placeholder="Pergunte sobre suas finanças..."
                    disabled={chatMut.isPending}
                    className="flex-1 h-11 rounded-xl border text-sm text-white placeholder-gray-600 px-4 focus:outline-none focus:border-brand-500/40"
                    style={{ background: "var(--color-surface-2)", borderColor: "var(--color-border)" }}
                  />
                  <Button onClick={() => send()} disabled={!input.trim() || chatMut.isPending}>
                    <Send size={14} />
                  </Button>
                </div>
                <p className="text-[10px] text-gray-600 mt-2 text-center">
                  ✨ Respostas geradas com IA baseadas em seus dados financeiros reais
                </p>
              </div>
            </Card>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
