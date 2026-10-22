# الاختبارات

## 1. تشغيل الاختبارات

```bash
cd backend
pip install -e ".[dev]"
.venv/bin/python -m pytest -q            # كل الاختبارات
.venv/bin/python -m pytest -m security   # اختبارات الصلاحيات فقط
.venv/bin/python -m pytest --cov=app --cov-report=term-missing
```

**لا حاجة لأي إعداد خارجي:** `tests/conftest.py` يشغّل PostgreSQL حقيقيًا (من
الملفات المُضمّنة في `embedded-postgres`) على منفذ عشوائي، ينشئ قاعدة
`clinic_test`، ينفّذ الترحيلات، ويمسح الجداول بين كل اختبارين.

### لماذا PostgreSQL حقيقي وليس SQLite؟
الضوابط التي نختبرها **لا يمكن** إعادة إنتاجها على SQLite:
قيد `EXCLUDE USING gist`، سياسات RLS، `pg_advisory_xact_lock`، عزل المعاملات
والمستويات (Read Committed). اختبارsimeq على SQLite كان سيعطي **نتيجة مضلّلة**.

### أدوار قاعدة البيانات في الاختبار
- التطبيق يتصل بـ `clinic_app` (دور **غير مالك** للجداول) → **تطبّق RLS فعليًا**.
- الإعداد/التشظيف يتصل بـ `postgres` (المالك) → كم DBA.
هذا يعني أن اختبارات الصلاحيات **تختبر ما سيُنشر فعلًا**، لا محاكاة.

## 2. ما تغطيه الاختبارات (62 اختبارًا)

### المواعيد (`tests/test_appointments.py`) — 14
| الاختبار | ما يثبته |
|---|---|
| `test_booking_succeeds_and_is_visible_to_owner` | دورة الحجز الأساسية + ظهورها لصاحب العيادة |
| `test_overlapping_booking_is_rejected_with_409` | تداخل ببداية مختلفة (10:15 مقابل 10:00) → `409` + نافذة التعارض |
| `test_booking_outside_working_hours_is_rejected` | `422 OUTSIDE_WORKING_HOURS` |
| `test_duplicate_booking_for_same_patient_is_rejected` | منع تكرار الحجز لنفس المريض |
| `test_cancelled_appointment_frees_the_slot` | الإلغاء يحرّر الفترة |
| `test_reschedule_conflict_leaves_the_original_untouched` | **إعادة الجدولة ذرّية**: عند التعارض يبقى الحجز الأصلي كما هو |
| `test_reschedule_moves_the_appointment` | إعادة الجدولة الناجحة |
| **`test_concurrent_bookings_only_one_wins`** | **10 طلبات متزامنة لنفس الوقت → واحد 201 وتسعة 409**، وصف واحد في القاعدة |
| `test_idempotency_key_prevents_double_submission` | نفس المفتاح لا ينشئ حجزًا ثانيًا |
| `test_reusing_an_idempotency_key_with_a_different_body_is_rejected` | `409 IDEMPOTENCY_KEY_REUSED` |
| `test_invalid_status_transition_is_rejected` | `409 INVALID_STATE_TRANSITION` |
| `test_doctor_sees_only_their_own_appointments` | عزل الصفوف بين الأطباء |
| `test_slots_endpoint_reports_unavailable_times` | الأوقات المتاحة تُحسب وتُحدَّث بعد الحجز |

### الصلاحيات والسرية (`tests/test_permissions.py`) — 18
| الاختبار | ما يثبته |
|---|---|
| `test_unauthenticated_request_is_rejected` | `401` بدون رمز |
| `test_invalid_token_is_rejected` | `401 INVALID_TOKEN` |
| `test_disabled_account_cannot_use_the_api` | `403 ACCOUNT_DISABLED` |
| `test_logout_invalidates_the_token_immediately` | **إنهاء الجلسة فعّال فورًا** (`401 SESSION_REVOKED`) |
| `test_owner_cannot_read_the_medical_record` | `403 MEDICAL_RECORD_FORBIDDEN` — لا loophole |
| `test_reception_cannot_read_the_medical_record` |同上 |
| `test_doctor_cannot_read_another_doctors_visit` | `404` (السطر غير مرئي أصلًا) |
| `test_doctor_can_read_their_own_visit` | الوصول الطبيعي |
| `test_explicit_grant_allows_another_doctor_to_read` | التفويض الصريح يعمل ويظهر `access_granted=true` |
| `test_reception_cannot_write_a_medical_record` | منع الكتابة الطبية |
| `test_doctor_only_sees_their_own_patients` | عزل المرضى |
| `test_owner_sees_patients_without_contact_details` | **لا حقل هاتف في استجابة صاحب العيادة** |
| `test_reception_sees_the_phone_number` | الريسبشن يرى الهاتف (لأغراض الحجز) |
| `test_reception_cannot_see_expenses` / `test_doctor_cannot_see_expenses` | المصروفات لصاحب العيادة |
| `test_doctor_cannot_read_the_audit_log` | السجل لصاحب العيادة |
| `test_doctor_cannot_read_the_weekly_report` | التقرير المالي لصاحب العيادة |
| `test_only_the_owner_can_create_staff_accounts` | إدارة الحسابات مقيّدة |

### الفوترة (`tests/test_billing.py`) — 12
مجموع الفاتورة من البنود، السداد الجزئي (المدفوع/المتبقي)، رفض الدفع
الأكثر من المتبقي (`422`)، اكتمال السداد، **رفض تخزين أرقام البطاقات**، منع
إلغاء فاتورة عليها مدفوعات، إلغاء الدفعة يعيد رصيد الفاتورة، **عرض
الإجماليات فقط للريسبشن** (بلا بنود)، منع الريسبشن من إلغاء فاتورة، تسجيل
المصروفات وإلغاؤها، ورفض المبالغ الصفرية.

### التقارير (`tests/test_reports.py`) — 4
فصل «إجمالي الفواتير» عن «المحصّل فعليًا»، حساب صافي النتيجة = المتحصلات −
المصروفات، استبعاد المدفوعات والمصروفات الملغاة، وأداء الأطباء والجداول.

### مسارات الأدوار (`tests/test_role_journeys.py`) — 4
| الاختبار | ما يثبته |
|---|---|
| `test_reception_journey_booking_to_collection` | المسار الكامل للريسبشن: مريض ← حجز ← تأكيد ← فاتورة ← تحصيل، مع التحقق من الأرصدة |
| `test_doctor_journey_visit_to_completion` | مسار الطبيب: الجدول ← فتح سجل ← إكماله ← إغلاق الموعد تلقائيًا |
| `test_owner_journey_report_staff_and_audit` | مسار صاحب العيادة: التقرير ← إنشاء/تعطيل موظف ← سجل التدقيق ← جدول الدوام |
| `test_role_journeys_do_not_leak_between_roles` | لا تسرّب بين الأدوار على نفس البيانات |

### سجل التدقيق (`tests/test_audit.py`) — 4
تسجيل عملية الحجز، **تسجيل قراءة الملف الطبي بدون نسخ المحتوى** (تحقّق نصّي:
لا التشخيص ولا العلاج ولا الملاحظات ولا اسم المريض في السجل)، **عدم إمكانية
تعديل السجل أو حذفه** (RLS + عدم وجود صلاحية DELETE)، وعدم تسريب تفاصيل
داخلية في رسائل الخطأ.

## 2.1 فحص دخان على خادم يعمل فعليًا

```bash
cd backend
ALLOW_DEV_SEED=1 python scripts/seed_dev_data.py     # مرة واحدة
uvicorn app.main:app --port 8000 &
./scripts/smoke_test.sh                               # 11 خطوة
```

يتحقق من: جاهزية الخدمة، الدخول للأدوار الثلاثة، قائمة الأطباء، تسجيل مريض،
الحجز، **رفض التعارض (409)**، الفاتورة، السداد الجزئي، **رفض رقم البطاقة**،
**منع الوصول غير المصرّح للأدوار الثلاثة**، التقرير الأسبوعي، والتنظيف.

## 2.2 اختبارات الواجهة (Vitest)

```bash
cd frontend
npm install
npm test          # 34 اختبارًا
npm run typecheck # tsc --noEmit
npm run lint      # ESLint
npm run build     # بناء الإنتاج (20 مسارًا)
```

| الملف | ما يغطّيه |
|---|---|
| `src/lib/__tests__/errors.test.ts` | الغلاف الموحّد للخطأ، عدم تسريب `detail` في 5xx، كشف `APPOINTMENT_CONFLICT` و`RESCHEDULE_CONFLICT` و`OUTSIDE_WORKING_HOURS` |
| `src/lib/__tests__/format.test.ts` | تنسيق المال (بلا أخطاء فاصلة عائمة)، وتحويل التواريخ إلى **توقيت العيادة** (UTC ← Africa/Cairo)، والأرقام العربية-الهندية |
| `src/lib/__tests__/permissions.test.ts` | إخفاء عناصر التنقل حسب الدور (صاحب العيادة لا يرى الملف الطبي، الطبيب لا يرى المصروفات، الريسبشن لا يرى التقرير المالي) |
| `src/components/__tests__/states.test.tsx` | حالات التحميل/الفراغ/الخطأ/النجاح + عدم تسريب التفاصيل الداخلية + إظهار `request_id` |
| `src/components/__tests__/dashboard-panel.test.tsx` | لوحة تحكم صاحب العيادة: تعرض أرقام الخادم، والتنبيه أن الصافي ليس ربحًا محاسبيًا، والحالة الفارغة |

**نتيجة آخر تشغيل:** `Test Files 5 passed (5)` · `Tests 34 passed (34)` ·
`tsc --noEmit` نظيف · `eslint` نظيف · `next build` نجح (20 مسارًا).

**لم يُنفَّذ:** اختبار E2E بمتصفح حقيقي (لا متصفح متاح في بيئة التنفيذ) —
يبقى اشتراطًا قبل الإنتاج (انظر `SECURITY_REVIEW.md` §5).

## 3. الفحوص الساكنة والأمان

```bash
cd backend
.venv/bin/ruff check app tests migrations scripts   # الأسلوب + الأخطاء الشائعة
.venv/bin/mypy app                                    # أنواع صارمة
.venv/bin/pip-audit                                   # ثغرات الاعتماديات
.venv/bin/python scripts/check_secrets.py             # أسرار مسرّبة في المستودع
```

أو كل الفحوص دفعة واحدة من جذر المشروع:

```bash
./scripts/verify_all.sh
```

**نتيجة آخر تشغيل (2026-10-20):**

| الفحص | النتيجة |
|---|---|
| `pytest` (62 اختبارًا) | **62 passed** |
| `ruff check` | **All checks passed** |
| `mypy app` | **Success: no issues found in 65 source files** |
| `pip-audit` | **No known vulnerabilities found** |
| `scripts/check_secrets.py` | **لم يُعثر على أسرار في المستودع** |
| `tsc --noEmit` + `eslint` (الواجهة) | **نظيف** |
| `next build` (الواجهة) | **ناجح — 20 مسارًا** |
| `npm audit --omit=dev` | **0 ثغرات في اعتماديات الإنتاج** |

## 4. ما **لم** يُختبر آليًا (حدود صريحة)

| المجال | الحالة | لماذا / ما يلزم |
|---|---|---|
| اختبار اختراق مستقل (PenTest) | ❌ | خارج نطاق التنفيذ الآلي — مطلوب قبل الإنتاج (SECURITY.md R8) |
| اختبار سعة/حِمل (Load test) | ❌ | لا حاجة مثبتة بعد؛ يُنصح به إن تجاوزت数百 المواعيد/ساعة |
| اختبار واجهة E2E (Playwright) | قيد التنفيذ مع الواجهة | يُنفَّذ داخل الواجهة |
| اختبار استعادة نسخة احتياطية | ❌ | موثّق في `RUNBOOK.md` §8.3 — **مطلوب تنفيذه فعليًا** |
| اختبار متصفح فعلي (Safari/iOS) | ❌ | لا أجهزة اختبار متاحة |
| مراجعة يدوية للواجهة (Usability) | ❌ | تحتاج مستخدمين فعليين من العيادة |

## 5. كيف تضيف اختبارًا

```python
# tests/test_example.py
from tests.helpers import Actor, clinic_monday, iso_at

async def test_something(client, reception: Actor, doctor: Actor, patient):
    response = await client.post("/api/v1/appointments", json={...}, headers=reception.headers)
    assert response.status_code == 201
```

- استخدم `db_session` (دور المالك) لإعداد البيانات، و`client` لاستدعاء الـ API
  (دور `clinic_app` — أي أن RLS مطبَّق).
- بيانات الاختبار اصطناعية بالكامل وتُحذف بعد كل اختبار.
