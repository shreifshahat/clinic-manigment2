import {
  useFieldControl,
} from "@/components/ui/field";
import type {
  InputHTMLAttributes,
  SelectHTMLAttributes,
  TextareaHTMLAttributes,
} from "react";

const BASE =
  "w-full rounded-lg border bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 disabled:bg-slate-100 disabled:text-slate-500";

function borderClass(invalid: boolean): string {
  return invalid
    ? "border-red-500 focus:border-red-600"
    : "border-slate-300 focus:border-brand-600";
}

export function TextInput({
  className = "",
  ...rest
}: InputHTMLAttributes<HTMLInputElement>) {
  const control = useFieldControl();
  return (
    <input
      id={control?.id}
      aria-describedby={control?.describedBy}
      aria-invalid={control?.invalid || undefined}
      className={`${BASE} ${borderClass(control?.invalid ?? false)} ${className}`}
      {...rest}
    />
  );
}

export function SelectInput({
  className = "",
  children,
  ...rest
}: SelectHTMLAttributes<HTMLSelectElement>) {
  const control = useFieldControl();
  return (
    <select
      id={control?.id}
      aria-describedby={control?.describedBy}
      aria-invalid={control?.invalid || undefined}
      className={`${BASE} ${borderClass(control?.invalid ?? false)} ${className}`}
      {...rest}
    >
      {children}
    </select>
  );
}

export function TextArea({
  className = "",
  ...rest
}: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  const control = useFieldControl();
  return (
    <textarea
      id={control?.id}
      aria-describedby={control?.describedBy}
      aria-invalid={control?.invalid || undefined}
      className={`${BASE} ${borderClass(control?.invalid ?? false)} min-h-24 resize-y ${className}`}
      {...rest}
    />
  );
}
