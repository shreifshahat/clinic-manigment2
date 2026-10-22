"use client";

import { useEffect, type ReactNode } from "react";
import { useRouter } from "next/navigation";

import { AppShell } from "@/components/app-shell";
import { LoadingState } from "@/components/ui/states";
import { useAuth } from "@/lib/auth";

export default function ProtectedLayout({ children }: { children: ReactNode }) {
  const { status } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (status === "anonymous" || status === "unconfigured") {
      router.replace("/login");
    }
  }, [status, router]);

  if (status !== "authenticated") {
    return (
      <main className="flex min-h-screen items-center justify-center">
        <LoadingState label="جارٍ التحقّق من الجلسة…" />
      </main>
    );
  }

  return <AppShell>{children}</AppShell>;
}
