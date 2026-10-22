"use client";

/**
 * لوحة سجل التدقيق (صاحب العيادة).
 *
 * سجل غير قابل للتعديل يعرض من فعل ماذا وبأي نتيجة. **لا يحتوي أي محتوى
 * طبي** — السجلات الطبية تُشار إليها بالمعرّف فقط.
 */

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { Field } from "@/components/ui/field";
import { TextInput } from "@/components/ui/input";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/states";
import { TableWrapper, Td, Th } from "@/components/ui/table";
import { useClinic } from "@/lib/clinic";
import { auditApi } from "@/lib/endpoints";
import { formatDateTime } from "@/lib/format";
import { AUDIT_OUTCOME_LABELS, ROLE_LABELS } from "@/lib/permissions";

export function AuditPanel() {
  const { timezone } = useClinic();
  const [action, setAction] = useState("");
  const [entityType, setEntityType] = useState("");
  const [applied, setApplied] = useState<{ action?: string; entity_type?: string }>({});

  const auditQuery = useQuery({
    queryKey: ["audit", applied.action, applied.entity_type],
    queryFn: () => auditApi.list({ ...applied, size: 100 }),
  });

  const rows = auditQuery.data?.items ?? [];

  return (
    <div className="flex flex-col gap-6">
      <Card>
        <CardHeader
          title="تصفية السجل"
          description="ابحث باسم العملية (مثل appointment.create) أو نوع السجل."
        />
        <CardBody>
          <form
            className="grid gap-4 sm:grid-cols-3"
            onSubmit={(event) => {
              event.preventDefault();
              setApplied({
                action: action.trim() || undefined,
                entity_type: entityType.trim() || undefined,
              });
            }}
          >
            <Field id="audit-action" label="العملية">
              <TextInput
                id="audit-action"
                type="text"
                value={action}
                onChange={(event) => setAction(event.target.value)}
                placeholder="appointment.create"
              />
            </Field>
            <Field id="audit-entity" label="نوع السجل">
              <TextInput
                id="audit-entity"
                type="text"
                value={entityType}
                onChange={(event) => setEntityType(event.target.value)}
                placeholder="visit"
              />
            </Field>
            <div className="flex items-end">
              <Button type="submit">تطبيق</Button>
            </div>
          </form>
        </CardBody>
      </Card>

      <Card>
        <CardHeader
          title="سجل العمليات"
          description="كل عملية حساسة موثّقة هنا بمعرّف الطلب (request_id)."
        />
        <CardBody>
          {auditQuery.isLoading ? <LoadingState /> : null}
          {auditQuery.isError ? (
            <ErrorState
              error={auditQuery.error}
              onRetry={() => void auditQuery.refetch()}
            />
          ) : null}
          {auditQuery.isSuccess && rows.length === 0 ? (
            <EmptyState
              title="لا توجد سجلات مطابقة"
              description="جرّب تغيير التصفية أوPeriod أطول."
            />
          ) : null}
          {rows.length > 0 ? (
            <TableWrapper>
              <thead>
                <tr>
                  <Th>الوقت</Th>
                  <Th>المنفّذ</Th>
                  <Th>الدور</Th>
                  <Th>العملية</Th>
                  <Th>السجل</Th>
                  <Th>النتيجة</Th>
                  <Th>معرّف الطلب</Th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.id}>
                    <Td className="whitespace-nowrap">
                      {formatDateTime(row.created_at, timezone)}
                    </Td>
                    <Td>{row.actor_role ? ROLE_LABELS[row.actor_role as never] ?? row.actor_role : "—"}</Td>
                    <Td className="text-xs">{row.actor_role || "—"}</Td>
                    <Td className="font-mono text-xs">{row.action}</Td>
                    <Td className="text-xs">
                      {row.entity_type}
                      {row.entity_id ? ` · ${row.entity_id.slice(0, 8)}` : ""}
                    </Td>
                    <Td>
                      <Badge tone={row.outcome === "success" ? "success" : "danger"}>
                        {AUDIT_OUTCOME_LABELS[row.outcome] ?? row.outcome}
                      </Badge>
                    </Td>
                    <Td className="font-mono text-[11px] text-slate-500">{row.request_id}</Td>
                  </tr>
                ))}
              </tbody>
            </TableWrapper>
          ) : null}
        </CardBody>
      </Card>
    </div>
  );
}
