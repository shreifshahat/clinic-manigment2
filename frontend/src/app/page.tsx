"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { LoadingState } from "@/components/ui/states";
import { useAuth } from "@/lib/auth";

export default function HomePage() {
  const { status } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (status === "authenticated") {
      router.replace("/dashboard");
    } else if (status === "anonymous" || status === "unconfigured") {
      router.replace("/login");
    }
  }, [status, router]);

  return (
    <main className="flex min-h-screen items-center justify-center">
      <LoadingState label="جارٍ التحقّق من الجلسة…" />
    </main>
  );
}
