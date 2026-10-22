"use client";

/**
 * لوحة المصروفات (صاحب العيادة فقط).
 *
 * تسجيل مصروف (مبلغ، تصنيف، تاريخ، وصف)، عرض القائمة، وإلغاء مصروف مسجَّل
 * مع سبب. لا يوجد تعديل لمصروف معتمد — التصحيح يتم بالإلغاء ثم التسجيل.
 */

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { Field } from "@/components/ui/field";
import { SelectInput, TextArea, TextInput } from "@/components/ui/input";
import {
  EmptyState,
  ErrorState,
  LoadingState,
  SuccessMessage,
} from "@/components/ui/states";
import { TableWrapper, Td, Th } from "@/components/ui/table";
import { useClinic } from "@/lib/clinic";
import { expensesApi } from "@/lib/endpoints";
import { formatDateTime, formatMoney } from "@/lib/format";
import { zodResolver } from "@/lib/zod-resolver";

const expenseSchema = z.object({
  amount: z
    .string()
    .trim()
    .regex(/^\d+(\.\d{1,2})?$/, "أدخل مبلغًا صحيحًا (رقمان عشريان كحد أقصى)."),
  description: z.string().trim().min(2, "اكتب وصفًا للمصروف."),
  categoryId: z.string().optional(),
  notes: z.string().max(1000).optional(),
});

type ExpenseValues = z.output<typeof expenseSchema>;

export function ExpensesPanel() {
  const { currency, currencyDecimals, timezone } = useClinic();
  const queryClient = useQueryClient();
  const [success, setSuccess] = useState<string | null>(null);

  const expensesQuery = useQuery({
    queryKey: ["expenses"],
    queryFn: () => expensesApi.list({ size: 50 }),
  });
  const categoriesQuery = useQuery({
    queryKey: ["expense-categories"],
    queryFn: expensesApi.categories,
  });

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<ExpenseValues>({
    resolver: zodResolver(expenseSchema),
    defaultValues: { amount: "", description: "", categoryId: "", notes: "" },
  });

  const createMutation = useMutation({
    mutationFn: expensesApi.create,
    onSuccess: async () => {
      reset({ amount: "", description: "", categoryId: "", notes: "" });
      setSuccess("تم تسجيل المصروف.");
      await queryClient.invalidateQueries({ queryKey: ["expenses"] });
    },
  });

  const voidMutation = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) =>
      expensesApi.void(id, reason),
    onSuccess: async () => {
      setSuccess("تم إلغاء المصروف.");
      await queryClient.invalidateQueries({ queryKey: ["expenses"] });
    },
  });

  function onSubmit(values: ExpenseValues) {
    createMutation.mutate({
      amount: values.amount,
      description: values.description,
      category_id: values.categoryId ? values.categoryId : null,
      notes: values.notes ?? "",
    });
  }

  const rows = expensesQuery.data?.items ?? [];

  return (
    <div className="flex flex-col gap-6">
      <Card>
        <CardHeader
          title="تسجيل مصروف"
          description="المصروف المسجَّل لا يُعدَّل ولا يُحذف — يُلغى بسبب، ثم يُسجَّل قيد جديد."
        />
        <CardBody>
          <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <Field
                id="expense-amount"
                label="المبلغ"
                required
                error={errors.amount?.message}
                hint={`بالـ ${currency}`}
              >
                <TextInput
                  type="text"
                  inputMode="decimal"
                  placeholder="0.00"
                  {...register("amount")}
                />
              </Field>
              <Field id="expense-category" label="التصنيف" error={errors.categoryId?.message}>
                <SelectInput {...register("categoryId")}>
                  <option value="">بدون تصنيف</option>
                  {(categoriesQuery.data ?? []).map((category) => (
                    <option key={category.id} value={category.id}>
                      {category.name}
                    </option>
                  ))}
                </SelectInput>
              </Field>
            </div>
            <Field
              id="expense-description"
              label="الوصف"
              required
              error={errors.description?.message}
            >
              <TextInput
                type="text"
                placeholder="مثال: مستلزمات طبية"
                {...register("description")}
              />
            </Field>
            <Field id="expense-notes" label="ملاحظات" error={errors.notes?.message}>
              <TextArea placeholder="تفاصيل إضافية (اختياري)" {...register("notes")} />
            </Field>

            {createMutation.isError ? (
              <ErrorState error={createMutation.error} title="تعذّر تسجيل المصروف" />
            ) : null}
            {success ? <SuccessMessage>{success}</SuccessMessage> : null}

            <div>
              <Button type="submit" loading={isSubmitting || createMutation.isPending}>
                تسجيل المصروف
              </Button>
            </div>
          </form>
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="المصروفات المسجّلة" description="المصروفات الملغاة مستثناة من التقارير." />
        <CardBody>
          {expensesQuery.isLoading ? <LoadingState /> : null}
          {expensesQuery.isError ? (
            <ErrorState
              error={expensesQuery.error}
              onRetry={() => void expensesQuery.refetch()}
            />
          ) : null}
          {expensesQuery.isSuccess && rows.length === 0 ? (
            <EmptyState
              title="لا توجد مصروفات مسجّلة"
              description="سجّل أول مصروف من النموذج أعلاه."
            />
          ) : null}
          {rows.length > 0 ? (
            <TableWrapper>
              <thead>
                <tr>
                  <Th>الوصف</Th>
                  <Th>التصنيف</Th>
                  <Th>المبلغ</Th>
                  <Th>التاريخ</Th>
                  <Th>الحالة</Th>
                  <Th>إجراء</Th>
                </tr>
              </thead>
              <tbody>
                {rows.map((expense) => (
                  <tr key={expense.id}>
                    <Td>{expense.description}</Td>
                    <Td>{expense.category_name || "—"}</Td>
                    <Td className="font-medium">
                      {formatMoney(expense.amount, { currency, decimals: currencyDecimals })}
                    </Td>
                    <Td>{formatDateTime(expense.incurred_at, timezone)}</Td>
                    <Td>
                      <Badge tone={expense.status === "void" ? "danger" : "success"}>
                        {expense.status === "void" ? "ملغى" : "مسجّل"}
                      </Badge>
                    </Td>
                    <Td>
                      {expense.status === "recorded" ? (
                        <VoidExpenseButton
                          expenseId={expense.id}
                          onConfirm={(reason) =>
                            voidMutation.mutate({ id: expense.id, reason })
                          }
                          isPending={voidMutation.isPending && voidMutation.variables?.id === expense.id}
                        />
                      ) : (
                        <span className="text-xs text-slate-500">{expense.void_reason}</span>
                      )}
                    </Td>
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

function VoidExpenseButton({
  expenseId,
  onConfirm,
  isPending,
}: {
  expenseId: string;
  onConfirm: (reason: string) => void;
  isPending: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState("");

  if (!open) {
    return (
      <Button variant="secondary" size="sm" onClick={() => setOpen(true)}>
        إلغاء
      </Button>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      <label htmlFor={`void-reason-${expenseId}`} className="text-xs font-medium text-slate-700">
        سبب الإلغاء
      </label>
      <TextInput
        id={`void-reason-${expenseId}`}
        type="text"
        value={reason}
        onChange={(event) => setReason(event.target.value)}
        placeholder="مثال: سُجّل مرتين"
      />
      <div className="flex gap-2">
        <Button
          size="sm"
          variant="danger"
          loading={isPending}
          disabled={reason.trim().length < 3}
          onClick={() => onConfirm(reason.trim())}
        >
          تأكيد الإلغاء
        </Button>
        <Button size="sm" variant="ghost" onClick={() => setOpen(false)}>
          تراجع
        </Button>
      </div>
    </div>
  );
}
