import type { ReactNode } from "react";

/** جدول بسيط قابل للتمرير أفقيًا على الشاشات الصغيرة. */
export function TableWrapper({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={`overflow-x-auto ${className}`}>
      <table className="min-w-full border-collapse text-start text-sm">
        {children}
      </table>
    </div>
  );
}

export function Th({
  children,
  scope = "col",
  className = "",
  dir,
}: {
  children: ReactNode;
  scope?: "col" | "row";
  className?: string;
  dir?: "ltr" | "rtl";
}) {
  return (
    <th
      scope={scope}
      dir={dir}
      className={`border-b border-slate-200 bg-slate-50 px-3 py-2 text-start font-semibold text-slate-700 ${className}`}
    >
      {children}
    </th>
  );
}

export function Td({
  children,
  className = "",
  dir,
}: {
  children: ReactNode;
  className?: string;
  /** `ltr` للأرقام والرموز (أرقام الفواتير مثلًا) داخل جدول RTL. */
  dir?: "ltr" | "rtl";
}) {
  return (
    <td
      dir={dir}
      className={`border-b border-slate-100 px-3 py-2 align-top text-slate-800 ${className}`}
    >
      {children}
    </td>
  );
}
