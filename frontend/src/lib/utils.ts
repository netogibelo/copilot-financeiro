import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatCurrency(value: number): string {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
    minimumFractionDigits: 2,
  }).format(value);
}

function parseDate(dateStr: string | Date | null | undefined): Date | null {
  if (!dateStr) return null;
  if (dateStr instanceof Date) return isNaN(dateStr.getTime()) ? null : dateStr;
  // If it already has time info (T, space, or timezone), parse directly
  const hasTime = /[T\s]\d{2}:|Z|[+-]\d{2}:?\d{2}$/.test(dateStr);
  const d = hasTime ? new Date(dateStr) : new Date(dateStr + "T00:00:00");
  return isNaN(d.getTime()) ? null : d;
}

export function formatDate(dateStr: string | Date | null | undefined): string {
  const d = parseDate(dateStr);
  if (!d) return "-";
  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  }).format(d);
}

export function formatShortDate(dateStr: string | Date | null | undefined): string {
  const d = parseDate(dateStr);
  if (!d) return "-";
  return new Intl.DateTimeFormat("pt-BR", { day: "2-digit", month: "short" }).format(d);
}

export function formatMonthYear(month: number, year: number): string {
  return new Intl.DateTimeFormat("pt-BR", { month: "short", year: "numeric" })
    .format(new Date(year, month - 1));
}

export function getMonthName(month: number): string {
  return new Intl.DateTimeFormat("pt-BR", { month: "long" }).format(new Date(2024, month - 1));
}

export function currentMonthYear() {
  const now = new Date();
  return { month: now.getMonth() + 1, year: now.getFullYear() };
}

export function pluralize(n: number, singular: string, plural: string): string {
  return n === 1 ? singular : plural;
}

export function truncate(str: string, len: number): string {
  return str.length > len ? str.slice(0, len) + "…" : str;
}

export const TRANSACTION_TYPES = [
  { value: "receita", label: "Receita", color: "#22c55e" },
  { value: "despesa", label: "Despesa", color: "#f43f5e" },
  { value: "investimento", label: "Investimento", color: "#8b5cf6" },
  { value: "transferencia", label: "Transferência", color: "#6b7280" },
];

export const ACCOUNT_TYPES = [
  { value: "corrente", label: "Conta Corrente" },
  { value: "poupanca", label: "Poupança" },
  { value: "cartao_credito", label: "Cartão de Crédito" },
  { value: "investimento", label: "Investimento" },
  { value: "carteira", label: "Carteira" },
  { value: "outro", label: "Outro" },
];

export function typeColor(type: string): string {
  const map: Record<string, string> = {
    receita: "#22c55e",
    despesa: "#f43f5e",
    investimento: "#8b5cf6",
    transferencia: "#6b7280",
  };
  return map[type] || "#6b7280";
}

export function typeLabel(type: string): string {
  const map: Record<string, string> = {
    receita: "Receita",
    despesa: "Despesa",
    investimento: "Investimento",
    transferencia: "Transferência",
  };
  return map[type] || type;
}

export function typeClass(type: string): string {
  const map: Record<string, string> = {
    receita: "text-income",
    despesa: "text-expense",
    investimento: "text-investment",
    transferencia: "text-transfer",
  };
  return map[type] || "";
}
