"use client";
import { forwardRef } from "react";
import { cn } from "@/lib/utils";
import { Loader2, X } from "lucide-react";
import * as Dialog from "@radix-ui/react-dialog";

// ============== BUTTON ==============
interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "brand" | "ghost" | "danger" | "outline" | "secondary";
  size?: "sm" | "md" | "lg";
  loading?: boolean;
  leftIcon?: React.ReactNode;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "brand", size = "md", loading, leftIcon, children, disabled, ...props }, ref) => {
    const base = "inline-flex items-center justify-center gap-2 font-semibold rounded-xl transition-all focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed";
    const sizes = { sm: "h-8 px-3 text-xs", md: "h-10 px-4 text-sm", lg: "h-12 px-6 text-base" };
    const variants = {
      brand: "btn-brand text-white",
      ghost: "bg-transparent hover:bg-white/5 text-gray-400 hover:text-white",
      danger: "bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/20",
      outline: "bg-transparent border border-white/10 hover:border-brand-500/40 text-gray-300 hover:text-white",
      secondary: "text-gray-200 hover:bg-white/5",
    };
    const styleBg = variant === "secondary" ? { background: "var(--color-surface-2)" } : undefined;
    return (
      <button ref={ref} className={cn(base, sizes[size], variants[variant], className)} disabled={disabled || loading} style={styleBg} {...props}>
        {loading ? <Loader2 size={14} className="animate-spin" /> : leftIcon}
        {children}
      </button>
    );
  }
);
Button.displayName = "Button";

// ============== INPUT ==============
interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  leftIcon?: React.ReactNode;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, label, error, leftIcon, ...props }, ref) => (
    <div className="flex flex-col gap-1.5">
      {label && <label className="text-xs font-medium text-gray-400">{label}</label>}
      <div className="relative">
        {leftIcon && <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500">{leftIcon}</span>}
        <input ref={ref}
          className={cn("w-full h-10 rounded-xl border text-sm text-white placeholder-gray-600 transition-all focus:outline-none focus:border-brand-500/40",
            leftIcon ? "pl-10 pr-3" : "px-3",
            error && "border-rose-500/50",
            className
          )}
          style={{ background: "var(--color-surface-2)", borderColor: "var(--color-border)" }}
          {...props}
        />
      </div>
      {error && <p className="text-xs text-rose-400">{error}</p>}
    </div>
  )
);
Input.displayName = "Input";

// ============== SELECT ==============
interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  error?: string;
  options: { value: string; label: string }[];
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, label, error, options, ...props }, ref) => (
    <div className="flex flex-col gap-1.5">
      {label && <label className="text-xs font-medium text-gray-400">{label}</label>}
      <select ref={ref}
        className={cn("w-full h-10 rounded-xl border text-sm text-white px-3 focus:outline-none focus:border-brand-500/40 transition-all",
          error && "border-rose-500/50",
          className
        )}
        style={{ background: "var(--color-surface-2)", borderColor: "var(--color-border)" }}
        {...props}
      >
        <option value="" style={{ background: "#22262f" }}>Selecione...</option>
        {options.map((o) => (
          <option key={o.value} value={o.value} style={{ background: "#22262f" }}>{o.label}</option>
        ))}
      </select>
      {error && <p className="text-xs text-rose-400">{error}</p>}
    </div>
  )
);
Select.displayName = "Select";

// ============== TEXTAREA ==============
export const Textarea = forwardRef<HTMLTextAreaElement, React.TextareaHTMLAttributes<HTMLTextAreaElement> & { label?: string }>(
  ({ className, label, ...props }, ref) => (
    <div className="flex flex-col gap-1.5">
      {label && <label className="text-xs font-medium text-gray-400">{label}</label>}
      <textarea ref={ref}
        className={cn("w-full rounded-xl border text-sm text-white px-3 py-2 focus:outline-none focus:border-brand-500/40 resize-none", className)}
        style={{ background: "var(--color-surface-2)", borderColor: "var(--color-border)" }}
        {...props}
      />
    </div>
  )
);
Textarea.displayName = "Textarea";

// ============== CARD ==============
export function Card({ children, className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("card p-5", className)} {...props}>{children}</div>;
}

// ============== BADGE ==============
type BadgeVariant = "success" | "danger" | "warning" | "info" | "neutral" | "purple";

export function Badge({ children, variant = "neutral", className }: { children: React.ReactNode; variant?: BadgeVariant; className?: string }) {
  const map = {
    success: "bg-green-500/10 text-green-400 border-green-500/20",
    danger: "bg-rose-500/10 text-rose-400 border-rose-500/20",
    warning: "bg-amber-500/10 text-amber-400 border-amber-500/20",
    info: "bg-sky-500/10 text-sky-400 border-sky-500/20",
    neutral: "bg-white/5 text-gray-400 border-white/10",
    purple: "bg-violet-500/10 text-violet-400 border-violet-500/20",
  };
  return <span className={cn("inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium border", map[variant], className)}>{children}</span>;
}

// ============== MODAL ==============
interface ModalProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  children: React.ReactNode;
  maxWidth?: string;
}

export function Modal({ open, onClose, title, children, maxWidth = "max-w-lg" }: ModalProps) {
  return (
    <Dialog.Root open={open} onOpenChange={(o) => !o && onClose()}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm" />
        <Dialog.Content
          className={cn("fixed z-50 top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full p-6 rounded-2xl shadow-2xl", maxWidth)}
          style={{ background: "var(--color-surface-1)", border: "1px solid var(--color-border)" }}
        >
          {title && (
            <div className="flex items-center justify-between mb-5">
              <Dialog.Title className="text-base font-semibold text-white">{title}</Dialog.Title>
              <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-white/5 transition-colors">
                <X size={16} className="text-gray-500" />
              </button>
            </div>
          )}
          {children}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

// ============== STAT CARD ==============
interface StatCardProps {
  title: string;
  value: string;
  subtitle?: string;
  icon?: React.ReactNode;
  color?: string;
  trend?: { value: number; label: string };
  loading?: boolean;
}

export function StatCard({ title, value, subtitle, icon, color = "#22c55e", trend, loading }: StatCardProps) {
  if (loading) return (
    <div className="card p-5 space-y-3">
      <div className="shimmer h-3 w-24 rounded" />
      <div className="shimmer h-7 w-32 rounded" />
      <div className="shimmer h-2 w-20 rounded" />
    </div>
  );
  return (
    <div className="card p-5 group">
      <div className="flex items-start justify-between mb-3">
        <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">{title}</p>
        {icon && (
          <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0" style={{ background: `${color}15`, color }}>
            {icon}
          </div>
        )}
      </div>
      <p className="text-2xl font-bold text-white number-display mb-1">{value}</p>
      {subtitle && <p className="text-xs text-gray-500">{subtitle}</p>}
      {trend && (
        <div className="flex items-center gap-1 mt-2">
          <span className={cn("text-xs font-semibold", trend.value >= 0 ? "text-green-400" : "text-rose-400")}>
            {trend.value >= 0 ? "+" : ""}{trend.value.toFixed(1)}%
          </span>
          <span className="text-xs text-gray-600">{trend.label}</span>
        </div>
      )}
    </div>
  );
}

// ============== EMPTY STATE ==============
export function EmptyState({ icon, title, description, action }: {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      {icon && <div className="mb-4 text-gray-600">{icon}</div>}
      <p className="text-sm font-semibold text-gray-400 mb-1">{title}</p>
      {description && <p className="text-xs text-gray-600 mb-4 max-w-xs">{description}</p>}
      {action}
    </div>
  );
}

export function Spinner({ size = 20, className }: { size?: number; className?: string }) {
  return <Loader2 size={size} className={cn("animate-spin", className)} style={{ color: "#22c55e" }} />;
}

// ============== PAGE HEADER ==============
export function PageHeader({ title, description, actions }: {
  title: string;
  description?: string;
  actions?: React.ReactNode;
}) {
  return (
    <div className="flex items-start justify-between gap-4 mb-6">
      <div>
        <h1 className="text-2xl font-bold text-white">{title}</h1>
        {description && <p className="text-sm text-gray-500 mt-1">{description}</p>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}
