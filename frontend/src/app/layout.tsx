import type { Metadata, Viewport } from "next";

import { AppProviders } from "@/app/providers";
import "./globals.css";

export const metadata: Metadata = {
  title: "نظام إدارة العيادة",
  description: "نظام داخلي لإدارة مواعيد العيادة والمرضى والفواتير والتقارير.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ar" dir="rtl">
      <body className="min-h-screen bg-canvas text-slate-900">
        <AppProviders>{children}</AppProviders>
      </body>
    </html>
  );
}
