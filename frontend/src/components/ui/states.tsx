import type { ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { toApiError } from "@/lib/errors";

/** حالة التحميل: نص + مؤشر مرئي، ويُقرأ عبر `role="status"`. */
export function LoadingState({
  label = "جارٍ التحميل…",
  className = "",
}: {
  label?: string;
  className?: string;
}) {
  return (
    <div
      role="status"
      aria-live="polite"
      className={`flex items-center gap-3 py-8 text-sm text-slate-600 ${className}`}
    >
      <span
        aria-hidden="true"
        className="inline-block size-5 animate-spin rounded-full border-2 border-brand-600 border-t-transparent"
      />
      <span>{label}</span>
    </div>
  );
}

/** حالة فارغة: لا بيانات وهمية — رسالة واضحة فقط. */
export function EmptyState({
  title,
  description,
  action,
  className = "",
}: {
  title: string;
  description?: string;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`flex flex-col items-center gap-2 rounded-lg border border-dashed border-slate-300 bg-slate-50 px-4 py-10 text-center ${className}`}
    >
      <p className="text-sm font-semibold text-slate-700">{title}</p>
      {description ? (
        <p className="max-w-md text-sm text-slate-600">{description}</p>
      ) : null}
      {action ? <div className="mt-2">{action}</div> : null}
    </div>
  );
}

/** رسالة نجاح (aria-live لطيفة). */
export function SuccessMessage({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      role="status"
      aria-live="polite"
      className={`rounded-lg border border-emerald-300 bg-emerald-50 px-4 py-3 text-sm font-medium text-emerald-900 ${className}`}
    >
      {children}
    </div>
  );
}

/**
 * عرض خطأ موحّد: الرسالة العربية القادمة من الخادم + `request_id`
 * ليستطيع المستخدم مراجعة الدعم من مطابقة سجل الخادم.
 */
export function ErrorState({
  error,
  title = "تعذّر إتمام العملية",
  onRetry,
  className = "",
}: {
  error: unknown;
  title?: string;
  onRetry?: (() => void) | undefined;
  className?: string;
}) {
  const apiError = toApiError(error);
  return (
    <div
      role="alert"
      className={`rounded-lg border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-900 ${className}`}
    >
      <p className="font-semibold">{title}</p>
      <p className="mt-1">{apiError.message}</p>
      {apiError.requestId ? (
        <p className="mt-1 text-xs text-red-800">
          رقم الطلب: <code className="font-mono">{apiError.requestId}</code>
        </p>
      ) : null}
      {onRetry ? (
        <div className="mt-3">
          <Button variant="secondary" size="sm" onClick={onRetry}>
            إعادة المحاولة
          </Button>
        </div>
      ) : null}
    </div>
  );
}

/** تنبيه مضغوط (يستخدم داخل النماذج). */
export function ErrorAlert({
  error,
  className = "",
}: {
  error: unknown;
  className?: string;
}) {
  return <ErrorState error={error} className={className} />;
}
