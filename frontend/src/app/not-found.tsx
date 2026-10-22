import Link from "next/link";

/** صفحة «الصفحة غير موجودة» — واضحة وبديلة عملية. */
export default function NotFound() {
  return (
    <main className="flex min-h-screen items-center justify-center px-4">
      <div className="max-w-md text-center">
        <p className="text-4xl font-bold text-brand-700">404</p>
        <h1 className="mt-2 text-lg font-semibold text-slate-900">
          الصفحة المطلوبة غير موجودة
        </h1>
        <p className="mt-2 text-sm text-slate-600">
          ربما تم تغيير الرابط أو حذف الصفحة. استخدم القائمة الجانبية للوصول إلى
          ما تحتاجه.
        </p>
        <Link
          href="/dashboard"
          className="mt-6 inline-block rounded-lg bg-brand-700 px-4 py-2 text-sm font-medium text-white hover:bg-brand-800"
        >
          العودة إلى لوحة التحكم
        </Link>
      </div>
    </main>
  );
}
