"use client";

import { useEffect } from "react";
import Link from "next/link";

/**
 * حدّ الأخطاء على مستوى الصفحة.
 *
 * لا نعرض أي تفاصيل داخلية للمستخدم: نعرض رسالة عامة + زر إعادة المحاولة.
 * التفاصيل تُسجَّل في سجل الخادم مع `request_id`.
 */
export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("unhandled UI error", error.digest ?? "");
  }, [error]);

  return (
    <main className="flex min-h-screen items-center justify-center px-4">
      <div className="max-w-md text-center">
        <h1 className="text-lg font-semibold text-slate-900">
          حدث خطأ غير متوقع في هذه الشاشة
        </h1>
        <p className="mt-2 text-sm text-slate-600">
          لم تُنفَّذ العملية. أعد المحاولة، وإن تكرّر الخطأ تواصل مع مسؤول النظام.
        </p>
        {error.digest ? (
          <p className="mt-2 text-xs text-slate-500">
            رمز الخطأ: <code className="font-mono">{error.digest}</code>
          </p>
        ) : null}
        <div className="mt-6 flex items-center justify-center gap-3">
          <button
            type="button"
            onClick={reset}
            className="rounded-lg bg-brand-700 px-4 py-2 text-sm font-medium text-white hover:bg-brand-800"
          >
            إعادة المحاولة
          </button>
          <Link
            href="/dashboard"
            className="rounded-lg border border-slate-300 px-4 py-2 text-sm text-slate-700 hover:bg-slate-50"
          >
            لوحة التحكم
          </Link>
        </div>
      </div>
    </main>
  );
}
