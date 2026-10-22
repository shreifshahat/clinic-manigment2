# قاعدة البيانات

PostgreSQL 16+ مستضاف على **Supabase**. مصدر الحقيقة هو الترحيلات في
`backend/migrations/` (Alembic) + ملفات SQL في `backend/scripts/`.

## 1. كيف تُطبَّق الترحيلات

```bash
cd backend
alembic upgrade head          # تطبيق
alembic downgrade -1          # تراجع (لآخر ترحيل)
alembic revision --autogenerate -m "وصف"   # توليد بعد تعديل النماذج
```

الترحيلات الحالية:

| # | الملف | المحتوى |
|---|---|---|
| 1 | `20261020_2104_initial_schema.py` | 18 جدولًا + فهارس + قيود CHECK + مفاتيح أجنبية |
| 2 | `20261020_2110_row_level_security.py` | امتدادات، قيد منع التعارض، دوال مساعدة، سياسات RLS، مشغّلات حماية الحقول المالية، منح الصلاحيات |
| 3 | `20261020_2130_deactivate_reason.py` | عمود `patients.deactivate_reason` (سبب سحب السجل) |
| 4 | `20261020_2140_rate_limit.py` | جدول `rate_limit_counters` (عدّاد حدّ الطلبات المشترك بين العمليات) |

> **ملاحظة:** على Supabase تُنفَّذ الترحيلات من **مضيف قاعدة البيانات** (SQL Editor)
> أو من آلة عليها رابط الاتصال المباشر. `alembic` يحتاج `DATABASE_URL` بدور
> مالك الجداول.

## 2. مخطط الجداول

### الحسابات والأدوار

| الجدول | الأعمدة المهمة | ملاحظات |
|---|---|---|
| `staff` | `auth_user_id` (→ Supabase Auth), `role`, `full_name`, `email`, `is_active`, `must_change_password` | **لا يوجد عمود كلمة مرور**. `role ∈ {owner, doctor, receptionist}` |
| `doctors` | `staff_id` (PK → staff), `specialty`, `default_slot_minutes`, `consultation_fee`, `is_accepting_patients` | المفتاح هو `staff_id`为了让 سياسات RLS تقارن مباشرة |
| `doctor_working_hours` | `doctor_staff_id`, `weekday` (1=الاثنين..7=الأحد), `start_time`, `end_time` | أوقات محلية (بدون منطقة زمنية) |
| `doctor_breaks` | `doctor_staff_id`, `weekday`, `start_time`, `end_time`, `label` | لا يحجز الموعد داخلها |
| `doctor_leaves` | `doctor_staff_id`, `starts_at`, `ends_at` (timestamptz) | تمنع الحجز |
| `staff_sessions` | `staff_id`, `token_fingerprint` (unique), `revoked_at`, `revoked_reason`, `last_seen_at` | إنهاء صلاحية الوصول فورًا |

### المرضى والمواعيد والزيارات

| الجدول | ملاحظات |
|---|---|
| `patients` | الهوية والتواصل فقط. `notes` نص إداري (لا طبي). `deleted_at` = سحب ناعم، `deactivate_reason` = سبب السحب (إلزامي). |
| `appointments` | `starts_at`/`ends_at` = `timestamptz`، `status ∈ {pending, confirmed, in_progress, completed, cancelled, no_show}`، `version` للترقّي المتفائل. |
| `visits` | **الملف الطبي**: `chief_complaint`, `diagnosis`, `treatment`, `notes`, `vitals` (jsonb). لا سياسة RLSReading لغير الطبيب. |
| `visit_access_grants` | تفويض صريح: `visit_id`, `granted_doctor_staff_id`, `reason`, `expires_at`, `revoked_at`. |

### المال

| الجدول | ملاحظات |
|---|---|
| `services` | قائمة الخدمات والأسعار الافتراضية. |
| `invoices` | `invoice_number` فريد (`INV-<سنة>-<تسلسل>`)، `total NUMERIC(14,2)`، `status ∈ {issued, partially_paid, paid, void}`، حقول الإلغاء + السبب. |
| `invoice_items` | `quantity`, `unit_price`, `line_total` (محسوبة في التطبيق، ومقيدة بـ CHECK). |
| `payments` | `amount > 0`, `method ∈ {cash, visa}`, `status ∈ {recorded, void}`, `reference` قصير فقط. **لا حقل لرقم البطاقة ولا CVV**. |
| `expense_categories` / `expenses` | `status ∈ {recorded, void}` + سبب الإلغاء. |

### النظام

| الجدول | ملاحظات |
|---|---|
| `audit_log` | سجل **غير قابل للتعديل**: لا سياسة `UPDATE` ولا `DELETE`. `details` jsonb بقائمة مفاتيح مسموحة فقط (لا محتوى طبي). |
| `idempotency_keys` | فريد `(staff_id, key)` + بصمة الطلب + الاستجابة المخزّنة. |
| `rate_limit_counters` | عدّاد حدّ الطلبات لكل (مفتاح مجزّأ، دقيقة). **لا يحتوي بيانات شخصية** — المفتاح تجزئة مملّحة لعنوان العميل. |

## 3. منع تعارض المواعيد على مستوى القاعدة

```sql
alter table appointments
  add constraint no_overlap_per_doctor
  exclude using gist (
    doctor_staff_id with =,
    tstzrange(starts_at, ends_at) with &&
  )
  where (status in ('pending', 'confirmed', 'in_progress'));

create unique index uq_appointments_active_patient_slot
  on appointments (doctor_staff_id, patient_id, starts_at)
  where status in ('pending', 'confirmed', 'in_progress');
```

- `btree_gist` لازم لمقارنة `uuid` داخل قيد EXCLUDE.
- الحالات `cancelled` و`no_show` و`completed` **تحرّر** الفترة.
- أي `INSERT` يدوي من SQL Editor الذي يتعارض يُرفض من القاعدة نفسها.

## 4. سياسات RLS

كل الجداول الـ 18 عليها `enable row level security` (عدا `rate_limit_counters` وهو جدول تقني بلا بيانات شخصية) (من دون `force` — التوضيح في
`SECURITY.md`).

**دوال مساعدة** (كلها `SECURITY DEFINER` و`search_path` محدود):

| الدالة | الغرض |
|---|---|
| `app_current_staff_id()` | معرّف الموظف الحالي: من `app.user_id` (مسار الـ API) أو `auth.uid()` (المسار المباشر). |
| `app_current_staff_role()` | دور الموظف الحالي (من `app.role` أو من جدول `staff`). |
| `app_staff_by_auth_id(uuid)` | البحث عن الموظف أثناء مصافحة الجلسة (قبل ضبط سياق RLS). |
| `app_staff_by_email(text)` | نفس الشيء بالبريد (تطوير فقط). |
| `app_has_visit_access(uuid)` | هل يوجد تفويض حيّ؟ |
| `app_owns_visit(uuid)` | هل السجل للطبيب الحالي؟ |
| `app_doctor_treats_patient(uuid)` | هل للطبيب موعد مع المريض؟ |
| `app_can_read_invoice(uuid)` | هل يallowed الطبيب قراءة فاتورة عمله؟ |
| `app_doctor_directory()` | دليل الزملاء (اسم + تخصص) — لا يكشف شيئًا عن المرضى. |
| `app_is_active_doctor(uuid)` | التحقق من هدف التفويض. |

**ملخص السياسات حسب الجدول:**

| الجدول | قراءة | كتابة |
|---|---|---|
| `staff` | نفسي أو صاحب العيادة | صاحب العيادة فقط |
| `doctors`, `doctor_working_hours`, `doctor_breaks`, `doctor_leaves` | كل الموظفين | صاحب العيادة فقط |
| `patients` | الريسبشن/صاحب العيادة، والطبيب لمرضاه | الريسبشن/صاحب العيادة |
| `appointments` | صاحب العيادة/الريسبشن: الكل؛ الطبيب: مواعيده | صاحب العيادة/الريسبشن؛ الطبيب: مواعيده |
| `visits` | **الطبيب فقط**: سجلاته أو ما فُوِّض له | الطبيب صاحب السجل فقط |
| `visit_access_grants` | الممنوح/المانح/صاحب العيادة | صاحب العيادة أو الطبيب صاحب الملف |
| `invoices` | صاحب العيادة/الريسبشن: الكل؛ الطبيب: عمله | الريسبشن/صاحب العيادة (التعديل: صاحب العيادة) |
| `invoice_items` | حسب صلاحية الفاتورة | الريسبشن/صاحب العيادة |
| `payments` | صاحب العيادة/الريسبشن؛ الطبيب لعمله | الريسبشن/صاحب العيادة (التعديل: صاحب العيادة) |
| `expenses`, `expense_categories` | صاحب العيادة فقط | صاحب العيادة فقط |
| `audit_log` | صاحب العيادة فقط | إدراج من أي موظف (append-only) |
| `idempotency_keys` | صاحب المفتاح فقط | صاحب المفتاح فقط |
| `staff_sessions` | صاحب الجلسة أو صاحب العيادة | صاحب الجلسة |

## 5. منح الصلاحيات ومسار الوصول المباشر

```sql
-- دور التطبيق: مالكه ليس postgres، لذلك تنطبق عليه RLS دائمًا
create role clinic_app login password '…';
grant usage on schema public to clinic_app;
grant select, insert, update on all tables in schema public to clinic_app;
grant delete on doctor_working_hours, doctor_breaks, doctor_leaves to clinic_app;
grant usage, select on all sequences in schema public to clinic_app;
grant execute on all functions in schema public to clinic_app;

-- إغلاق المسار المباشر (PostgREST) أمام anon/authenticated
revoke all on all tables in schema public from anon;
revoke all on all tables in schema public from authenticated;
```

**النتيجة:** المتصفح لا يستطيع قراءة أي جدول مباشرة عبر مفتاح `anon`؛ كل
البيانات تمر عبر الـ API الذي يطبّق الطبقات الثلاث. ملف
`backend/scripts/create_db_role.sql` يطبّق ذلك يدويًا على أي قاعدة.

## 6. ثبات السجلات المالية (مشغّلات)

```sql
create trigger app_guard_invoice_update_trg before update on invoices …
```

المشغّلات تمنع تغيير `total` / `invoice_number` / `issued_at` / `patient_id` في
`invoices`، و`quantity`/`unit_price`/`line_total` في `invoice_items`، و`amount`/
`method`/`received_at` في `payments`، و`amount`/`incurred_at` في `expenses` — إلا
بصاحب العيادة. التصحيح = **إلغاء موثّق** (سبب + من نفّذ + وقت) + قيد جديد.

## 7. سياسة الاحتفاظ بالبيانات وحذفها

> **هذه السياسة تحتاج اعتماد صاحب العيادة قبل استخدام بيانات مرضى حقيقية**،
> ولم يُطبَّق شيء تلقائيًا على البيانات المنشأة.

| الفئة | قاعدة العمل الافتراضية (قابلة للتعديل) | التنفيذ |
|---|---|---|
| سجلات المرضى | سحب ناعم عند `is_active=false` + `deleted_at`، مع **إخفاء هوية** (استبدال الاسم بـ«مريض مسحوب») بعد انتهاء مدة الاحتفاظ | يدوي/مجدول |
| السجلات الطبية | **لا تُحذف**؛ تُحفظ وفق مدة الاحتفاظ الإلزامية في بلد التشغيل (مصر: لا تقل عن 5 سنوات وفق قانون حماية البيانات الشخصية 151/2020 ومBOSSiness التأهيلي) | لا يوجد `DELETE` في RLS إطلاقًا |
| الفواتير والمدفوعات والمصروفات | **لا تُحذف ولا تُعدَّل**؛ الإلغاء هو التصحيح | لا يوجد `DELETE` + مشغّلات |
| سجل التدقيق | يُحفظ indefinitely (كحد أدنى مدة الاحتفاظ المالي) | `append-only` |
| سجلات الجلسات | تُنظّف دوريًا بعد انتهاء صلاحيتها | مهمة housekeeping |

**حدود صريحة:**
- لا توجد أي سياسة `DELETE` في الجداول الحسّاسة، فالحذف غير ممكن حتى لمالك قاعدة البيانات عبر دور التطبيق.
- `ON DELETE RESTRICT` على العلاقات الطبية والمالية يمنع الحذف المتسلسل.
- الحذف الفعلي (Hard delete) لازم يتطلب **خطة موثّقة** من مالك البيانات — غير منفّذة حتى الآن.

## 8. النسخ الاحتياطي والاستعادة

انظر `RUNBOOK.md` (قسم 8): نسخة يومية `pg_dump` + WAL للعContinuous، واختبار
استعادة ربع سنوي على قاعدة منفصلة.
