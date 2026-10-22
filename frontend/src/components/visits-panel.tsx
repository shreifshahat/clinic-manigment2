"use client";

/**
 * لوحة الزيارات (الطبيب فقط).
 *
 * فتح/تعديل سجل زيارة (الشكوى الرئيسية، التشخيص، العلاج، الملاحظات،
 * القراءات الحيوية) ثم إكمال الكشف.
 */

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { VisitForm } from "@/components/visit-form";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import {
  EmptyState,
  ErrorState,
  LoadingState,
  SuccessMessage,
} from "@/components/ui/states";
import { useClinic } from "@/lib/clinic";
import { appointmentsApi, visitsApi } from "@/lib/endpoints";
import { formatDateTime, localDateTimeToIso } from "@/lib/format";
import type { AppointmentRead, VisitRead } from "@/lib/api-types";

export function VisitsPanel() {
  const { timezone, today, session } = useClinic();
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState<VisitRead | null>(null);
  const [opening, setOpening] = useState<AppointmentRead | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const visitsQuery = useQuery({
    queryKey: ["visits"],
    queryFn: () => visitsApi.list({ size: 50 }),
  });

  const dayAppointmentsQuery = useQuery({
    queryKey: ["visits", "day", today],
    queryFn: () =>
      appointmentsApi.list({
        date_from: localDateTimeToIso(today, "00:00", timezone),
        date_to: localDateTimeToIso(today, "23:59", timezone),
        size: 50,
      }),
  });

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ["visits"] });
    void queryClient.invalidateQueries({ queryKey: ["appointments"] });
  };

  const completeMutation = useMutation({
    mutationFn: (visitId: string) => visitsApi.complete(visitId),
    onSuccess: () => {
      setMessage("تم اكتمال سجل الزيارة.");
      invalidate();
    },
  });

  const visits = visitsQuery.data?.items ?? [];
  const dayAppointments = dayAppointmentsQuery.data?.items ?? [];
  const openable = dayAppointments.filter(
    (appointment) =>
      appointment.status === "confirmed" || appointment.status === "in_progress",
  );

  return (
    <div className="space-y-6">
      {message ? <SuccessMessage>{message}</SuccessMessage> : null}

      {opening ? (
        <VisitForm
          title="فتح سجل زيارة"
          appointment={opening}
          doctorStaffId={session?.staff_id ?? ""}
          onCancel={() => setOpening(null)}
          onSaved={() => {
            setOpening(null);
            setMessage("تم فتح سجل الزيارة.");
            invalidate();
          }}
        />
      ) : null}

      {editing ? (
        <VisitForm
          title="تعديل سجل الزيارة"
          visit={editing}
          onCancel={() => setEditing(null)}
          onSaved={() => {
            setEditing(null);
            setMessage("تم تحديث سجل الزيارة.");
            invalidate();
          }}
        />
      ) : null}

      <Card>
        <CardHeader
          title="مواعيد اليوم القابلة للكشف"
          description="افتح سجل زيارة لموعد بدأ أو بدأ فحصه."
        />
        <CardBody>
          {dayAppointmentsQuery.isLoading ? (
            <LoadingState label="جارٍ تحميل مواعيد اليوم…" />
          ) : dayAppointmentsQuery.isError ? (
            <ErrorState
              error={dayAppointmentsQuery.error}
              onRetry={() => void dayAppointmentsQuery.refetch()}
            />
          ) : openable.length === 0 ? (
            <EmptyState
              title="لا توجد مواعيد قابلة للكشف اليوم"
              description="تظهر هنا المواعيد المؤكدة أو قيد الكشف."
            />
          ) : (
            <ul className="space-y-2">
              {openable.map((appointment) => (
                <li
                  key={appointment.id}
                  className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-slate-50 px-3 py-2 text-sm"
                >
                  <div>
                    <span dir="ltr" className="font-medium">
                      {formatDateTime(appointment.starts_at, timezone)}
                    </span>
                    <span className="ms-3 text-slate-700">
                      {appointment.patient?.full_name ?? "—"}
                    </span>
                  </div>
                  <Button size="sm" variant="secondary" onClick={() => setOpening(appointment)}>
                    فتح زيارة
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="سجلات الزيارات" description="الزيارات الخاصة بك والمُفوَّض لك بها." />
        <CardBody>
          {visitsQuery.isLoading ? (
            <LoadingState label="جارٍ تحميل الزيارات…" />
          ) : visitsQuery.isError ? (
            <ErrorState
              error={visitsQuery.error}
              onRetry={() => void visitsQuery.refetch()}
            />
          ) : visits.length === 0 ? (
            <EmptyState
              title="لا توجد سجلات زيارات"
              description="افتح أول زيارة من مواعيد اليوم."
            />
          ) : (
            <ul className="space-y-3">
              {visits.map((visit) => (
                <li key={visit.id} className="rounded-lg border border-slate-200 p-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <p className="text-sm font-semibold text-slate-900">
                        {visit.patient?.full_name ?? "—"}
                      </p>
                      <p className="text-xs text-slate-600">
                        {formatDateTime(visit.created_at, timezone)} —{" "}
                        {visit.doctor_name || "—"}
                      </p>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      {visit.access_granted ? (
                        <Badge tone="brand">بتفويض</Badge>
                      ) : null}
                      <Badge tone={visit.is_completed ? "success" : "warning"}>
                        {visit.is_completed ? "مكتملة" : "مفتوحة"}
                      </Badge>
                      <Button size="sm" variant="ghost" onClick={() => setEditing(visit)}>
                        تعديل
                      </Button>
                      {!visit.is_completed ? (
                        <Button
                          size="sm"
                          variant="secondary"
                          loading={completeMutation.isPending}
                          onClick={() => completeMutation.mutate(visit.id)}
                        >
                          إكمال الكشف
                        </Button>
                      ) : null}
                    </div>
                  </div>
                  <dl className="mt-2 grid gap-1 text-sm text-slate-700 sm:grid-cols-2">
                    <div>
                      <dt className="inline font-medium">الشكوى الرئيسية: </dt>
                      <dd className="inline">{visit.chief_complaint || "—"}</dd>
                    </div>
                    <div>
                      <dt className="inline font-medium">التشخيص: </dt>
                      <dd className="inline">{visit.diagnosis || "—"}</dd>
                    </div>
                    <div>
                      <dt className="inline font-medium">العلاج: </dt>
                      <dd className="inline">{visit.treatment || "—"}</dd>
                    </div>
                    <div>
                      <dt className="inline font-medium">القراءات الحيوية: </dt>
                      <dd className="inline">
                        {Object.entries(visit.vitals ?? {})
                          .map(([key, value]) => `${key}: ${value}`)
                          .join(" — ") || "—"}
                      </dd>
                    </div>
                  </dl>
                </li>
              ))}
            </ul>
          )}
        </CardBody>
      </Card>
    </div>
  );
}
