import type { ReactNode } from "react";

export type BadgeTone =
  | "neutral"
  | "info"
  | "success"
  | "warning"
  | "danger"
  | "brand";

const TONES: Record<BadgeTone, string> = {
  neutral: "bg-slate-100 text-slate-700 ring-slate-300",
  info: "bg-sky-50 text-sky-800 ring-sky-300",
  success: "bg-emerald-50 text-emerald-800 ring-emerald-300",
  warning: "bg-amber-50 text-amber-900 ring-amber-300",
  danger: "bg-red-50 text-red-800 ring-red-300",
  brand: "bg-brand-50 text-brand-800 ring-brand-300",
};

export function Badge({
  children,
  tone = "neutral",
  className = "",
}: {
  children: ReactNode;
  tone?: BadgeTone;
  className?: string;
}) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset ${TONES[tone]} ${className}`}
    >
      {children}
    </span>
  );
}
