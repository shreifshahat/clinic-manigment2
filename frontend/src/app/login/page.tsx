"use client";

import { useEffect, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { Field } from "@/components/ui/field";
import { TextInput } from "@/components/ui/input";
import { ErrorState, LoadingState } from "@/components/ui/states";
import { isSupabaseConfigured, useAuth } from "@/lib/auth";
import { devLogin, isDevAuthEnabled } from "@/lib/dev-auth";

export default function LoginPage() {
  const { status, signIn, signInWithToken } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (status === "authenticated") {
      router.replace("/dashboard");
    }
  }, [status, router]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting) return;
    setError(null);
    setSubmitting(true);
    const message = await signIn(email, password);
    setSubmitting(false);
    if (message) {
      setError(message);
      return;
    }
    router.replace("/dashboard");
  }

  async function handleDevSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting) return;
    setError(null);
    setSubmitting(true);
    const result = await devLogin(email);
    setSubmitting(false);
    if (result.error) {
      setError(result.error);
      return;
    }
    signInWithToken(result.token ?? "", email.trim());
    router.replace("/dashboard");
  }

  if (status === "unconfigured" || !isSupabaseConfigured) {
    if (isDevAuthEnabled) {
      return (
        <main className="flex min-h-screen items-center justify-center p-4">
          <Card className="w-full max-w-md">
            <CardHeader
              title="تسجيل الدخول (وضع التطوير)"
              description="لم يُضبط مزوّد المصادقة. استخدم بريد حساب موجود في قاعدة التطوير."
            />
            <CardBody>
              <form onSubmit={handleDevSubmit} noValidate className="space-y-4">
                <Field id="dev-email" label="البريد الإلكتروني" required>
                  <TextInput
                    id="dev-email"
                    type="email"
                    dir="ltr"
                    placeholder="owner@clinic.local"
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    required
                  />
                </Field>
                {error ? (
                  <ErrorState error={new Error(error)} title="تعذّر تسجيل الدخول" />
                ) : null}
                <Button type="submit" loading={submitting} className="w-full">
                  {submitting ? "جارٍ الدخول…" : "دخول"}
                </Button>
                <p className="text-xs text-slate-500">
                  هذه الشاشة تعمل فقط في بيئة التطوير ومع تفعيل
                  ‎<code className="font-mono">NEXT_PUBLIC_ENABLE_DEV_LOGIN=true</code>‎.
                </p>
              </form>
            </CardBody>
          </Card>
        </main>
      );
    }

    return (
      <main className="flex min-h-screen items-center justify-center p-4">
        <Card className="w-full max-w-lg">
          <CardHeader
            title="خدمة المصادقة غير مهيّأة"
            description="لا يمكن تسجيل الدخول قبل ضبط متغيّرات البيئة التالية."
          />
          <CardBody>
            <ul className="list-inside list-disc space-y-1 text-sm text-slate-700">
              <li dir="ltr" className="font-mono text-start">
                NEXT_PUBLIC_SUPABASE_URL
              </li>
              <li dir="ltr" className="font-mono text-start">
                NEXT_PUBLIC_SUPABASE_ANON_KEY
              </li>
            </ul>
            <p className="mt-3 text-sm text-slate-600">
              انسخ ملف ‎<code className="font-mono">.env.example</code>‎ إلى ‎
              <code className="font-mono">.env.local</code>‎ وأعد تشغيل الخادم.
            </p>
          </CardBody>
        </Card>
      </main>
    );
  }

  if (status === "loading") {
    return (
      <main className="flex min-h-screen items-center justify-center">
        <LoadingState label="جارٍ التحقّق من الجلسة…" />
      </main>
    );
  }

  return (
    <main className="flex min-h-screen items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <CardHeader
          title="تسجيل الدخول"
          description="أدخل بيانات حساب الموظف للمتابعة إلى النظام."
        />
        <CardBody>
          <form onSubmit={handleSubmit} noValidate className="space-y-4">
            <Field id="email" label="البريد الإلكتروني" required>
              <TextInput
                type="email"
                name="email"
                autoComplete="username"
                required
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                dir="ltr"
                placeholder="name@clinic.com"
              />
            </Field>
            <Field id="password" label="كلمة المرور" required>
              <TextInput
                type="password"
                name="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                dir="ltr"
              />
            </Field>

            {error ? <ErrorState error={new Error(error)} title="تعذّر تسجيل الدخول" /> : null}

            <Button type="submit" loading={submitting} className="w-full">
              {submitting ? "جارٍ الدخول…" : "دخول"}
            </Button>
          </form>
        </CardBody>
      </Card>
    </main>
  );
}
