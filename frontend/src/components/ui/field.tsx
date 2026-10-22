import { createContext, useContext, type ReactNode } from "react";

/**
 * غلاف لعناصر النماذج: تسمية مرتبطة، نص إرشادي، ورسالة خطأ
 * موصولة بالحقل عبر `aria-describedby`.
 */
export function Field({
  id,
  label,
  hint,
  error,
  required,
  children,
  className = "",
}: {
  id: string;
  label: string;
  hint?: string;
  error?: string | undefined;
  required?: boolean;
  children: ReactNode;
  className?: string;
}) {
  const hintId = hint ? `${id}-hint` : undefined;
  const errorId = error ? `${id}-error` : undefined;
  const describedBy = [hintId, errorId].filter(Boolean).join(" ") || undefined;

  return (
    <div className={`flex flex-col gap-1.5 ${className}`}>
      <label htmlFor={id} className="text-sm font-medium text-slate-800">
        {label}
        {required ? (
          <span className="text-red-700" aria-hidden="true">
            {" "}
            *
          </span>
        ) : null}
      </label>
      {hint ? (
        <p id={hintId} className="text-xs text-slate-600">
          {hint}
        </p>
      ) : null}
      <FieldControlContext.Provider value={{ id, describedBy, invalid: Boolean(error) }}>
        {children}
      </FieldControlContext.Provider>
      {error ? (
        <p id={errorId} role="alert" className="text-sm font-medium text-red-700">
          {error}
        </p>
      ) : null}
    </div>
  );
}

interface FieldControlContextValue {
  id: string;
  describedBy: string | undefined;
  invalid: boolean;
}

const FieldControlContext = createContext<FieldControlContextValue | null>(null);

/** يقرأ معرّف الحقل ووصفه من `Field` ليربطهما آليًا. */
export function useFieldControl(): FieldControlContextValue | null {
  return useContext(FieldControlContext);
}
