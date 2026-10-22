"use client";

import type { ButtonHTMLAttributes, ReactNode } from "react";

type Variant = "primary" | "secondary" | "ghost" | "danger" | "success";
type Size = "sm" | "md";

const VARIANTS: Record<Variant, string> = {
  primary:
    "bg-brand-700 text-white hover:bg-brand-800 disabled:bg-brand-700/50 shadow-sm",
  secondary:
    "bg-white text-slate-800 border border-slate-300 hover:bg-slate-50 disabled:opacity-60",
  ghost: "bg-transparent text-brand-800 hover:bg-brand-50 disabled:opacity-60",
  danger:
    "bg-red-700 text-white hover:bg-red-800 disabled:bg-red-700/50 shadow-sm",
  success: "bg-emerald-700 text-white hover:bg-emerald-800 disabled:opacity-60",
};

const SIZES: Record<Size, string> = {
  sm: "text-sm px-3 py-1.5 gap-1.5",
  md: "text-sm px-4 py-2 gap-2",
};

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  /** يعرض مؤشر انتظار وتعطّل الزر لمنع الإرسال المزدوج. */
  loading?: boolean;
  children?: ReactNode;
}

export function Button({
  variant = "primary",
  size = "md",
  loading = false,
  disabled,
  className = "",
  children,
  type = "button",
  ...rest
}: ButtonProps) {
  return (
    <button
      type={type}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={`inline-flex items-center justify-center rounded-lg font-medium transition-colors disabled:cursor-not-allowed ${VARIANTS[variant]} ${SIZES[size]} ${className}`}
      {...rest}
    >
      {loading ? (
        <span
          aria-hidden="true"
          className="inline-block size-4 animate-spin rounded-full border-2 border-current border-t-transparent"
        />
      ) : null}
      {children}
    </button>
  );
}
