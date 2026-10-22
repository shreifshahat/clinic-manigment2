import type { NextConfig } from "next";

const apiOrigin = (() => {
  const raw = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";
  try {
    return new URL(raw).origin;
  } catch {
    return "http://localhost:8000";
  }
})();

const supabaseOrigin = (() => {
  const raw = process.env.NEXT_PUBLIC_SUPABASE_URL ?? "";
  try {
    return new URL(raw).origin;
  } catch {
    return "";
  }
})();

/**
 * سياسة أمن المحتوى (CSP).
 *
 * `next dev` يحتاج `'unsafe-eval'`؛ الإنتاج لا يحتاجه.
 * `connect-src` يسمح بالاتصال بالـ API ومزوّد المصادقة فقط.
 */
function contentSecurityPolicy(isDev: boolean): string {
  const connectSources = ["'self'", apiOrigin, supabaseOrigin]
    .filter(Boolean)
    .join(" ");
  return [
    "default-src 'self'",
    `script-src 'self' 'unsafe-inline'${isDev ? " 'unsafe-eval'" : ""}`,
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: blob:",
    "font-src 'self' data:",
    `connect-src ${connectSources}`,
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "object-src 'none'",
    "upgrade-insecure-requests",
  ].join("; ");
}

const nextConfig: NextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  // The clinic API is a separate FastAPI service; the browser talks to it
  // directly through NEXT_PUBLIC_API_BASE_URL (no rewrite needed).
  env: {
    NEXT_PUBLIC_API_BASE_URL:
      process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1",
  },
  async headers() {
    const isDev = process.env.NODE_ENV !== "production";
    const csp = contentSecurityPolicy(isDev);
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "Content-Security-Policy", value: csp },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Referrer-Policy", value: "no-referrer" },
          {
            key: "Permissions-Policy",
            value: "geolocation=(), camera=(), microphone=()",
          },
        ],
      },
    ];
  },
};

export default nextConfig;
