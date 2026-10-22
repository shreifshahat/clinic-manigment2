# توثيق الـ API

المواصفات الكاملة (OpenAPI 3.1) مولّدة تلقائيًا ومتاحة على:

- أثناء التشغيل: `http://localhost:8000/docs` (Swagger) و `http://localhost:8000/openapi.json`
- نسخة ثابتة في المستودع: [`docs/openapi.json`](./openapi.json)

## 1. الأساس

| البند | القيمة |
|---|---|
| Base URL | `http://localhost:8000/api/v1` (يُضبط في الواجهة عبر `NEXT_PUBLIC_API_BASE_URL`) |
| المصادقة | `Authorization: Bearer <Supabase access token>` |
| نوع المحتوى | `application/json; charset=utf-8` |
| معرّف التتبع | ترويسة `X-Request-ID` (تُولَّد إن لم تُرسل) وتظهر في كل خطأ |
| المنطقة الزمنية | كل الأوقات تُخزَّن UTC وتُعاد بصيغة ISO-8601 بتوقيت `Z` |
| العملة | `EGP` بمنزلتين عشريتين، تُنقل كنص (`"400.00"`) لا كعدد عشري |

###dua دورة الطلب
```
POST /api/v1/appointments
Authorization: Bearer eyJhbGciOi...
Content-Type: application/json
Idempotency-Key: 5f2c...            ← اختياري لكن موصى به لعمليات الإنشاء
```

## 2. بنية الخطأ الموحّدة

كل خطأ (-validation, auth, تعارض، خطأ داخلي) يرجع بالشكل نفسه:

```json
{
  "error": {
    "code": "APPOINTMENT_CONFLICT",
    "message": "هذا الموعد لم يعد متاحًا. اختر موعدًا آخر.",
    "details": {
      "conflicting_starts_at": "2026-01-05T08:00:00Z",
      "conflicting_ends_at": "2026-01-05T08:30:00Z"
    },
    "request_id": "b1f0c1de2a6b4f4f9b1a8f2f4a1c9d21"
  }
}
```

- `code` ثابت ويُستخدم برمجيًا (لا يُغيَّر إلا بإصدار موثّق).
- `message` بالعربية وموجّه للمستخدم، ولا يحتوي أسرارًا ولا استعلامات SQL ولا بيانات مرضى.
- `details` يحتوي سياقًا آمنًا فقط (لا محتوى طبي، لا اسم مريض).
- `request_id` يُستخدم في الدعم: نفس المعرّف في سجل الخادم.

### جدول الأكواد

| HTTP | `code` | متى |
|---|---|---|
| 400 | `BAD_REQUEST` | طلب غير صالح |
| 401 | `AUTHENTICATION_REQUIRED` | لا يوجد رمز |
| 401 | `INVALID_TOKEN` | رمز منتهي/تلاعب/غير صحيح |
| 401 | `SESSION_REVOKED` | أُنهيت الجلسة (خروج/تعطيل/إعادة تعيين) |
| 403 | `FORBIDDEN` | لا صلاحية للعملية |
| 403 | `ACCOUNT_DISABLED` | الحساب معطّل |
| 403 | `PASSWORD_CHANGE_REQUIRED` | الحساب ما زال على كلمة المرور المؤقتة (يُمنع أي عمل except تغييرها) |
| 403 | `MEDICAL_RECORD_FORBIDDEN` | الملف الطبي خارج نطاق الدور |
| 404 | `NOT_FOUND` / `PATIENT_NOT_FOUND` / `VISIT_NOT_FOUND` / … | العنصر غير موجود أو غير مرئي |
| 409 | `APPOINTMENT_CONFLICT` | تعارض حجز |
| 409 | `RESCHEDULE_CONFLICT` | وقت إعادة الجدولة محجوز (الحجز الأصلي لم يتغيّر) |
| 409 | `DUPLICATE_BOOKING` | حجز مطابق موجود |
| 409 | `INVALID_STATE_TRANSITION` | انتقال حالة غير مسموح |
| 409 | `IDEMPOTENCY_KEY_REUSED` | نفس المفتاح بمحتوى مختلف |
| 409 | `INVOICE_ALREADY_VOID` / `PAYMENT_ALREADY_VOID` / `EXPENSE_ALREADY_VOID` | إلغاء مكرّر |
| 422 | `VALIDATION_ERROR` | فشل تحقق المخطط (الحقول في `details.fields`) |
| 422 | `OUTSIDE_WORKING_HOURS` | خارج الدوام/الاستراحة/الإجازة |
| 422 | `PAYMENT_EXCEEDS_REMAINING` | المبلغ أكبر من المتبقي |
| 429 | `RATE_LIMITED` | تجاوز حد الطلبات |
| 500 | `INTERNAL_ERROR` | خطأ غير متوقع (لا تفاصيل داخلية) |

## 3. الترقيم والتصفية

كل القوائم ترجع:

```json
{ "items": [ … ], "meta": { "page": 1, "size": 20, "total": 57, "pages": 3 } }
```

- `page` يبدأ من 1، و`size` بين 1 و100 (الافتراضي 20).
- معاملات التصفية الشائعة: `status`, `doctor_staff_id`, `patient_id`, `date_from`, `date_to`, `search`.
- التواريخ في الاستعلامات تُقبل بصيغة ISO-8601 **مع** إزاحة زمنية.

## 4. منع التكرار (Idempotency)

أرسل `Idempotency-Key: <uuid>` مع `POST` الخاصة بالإنشاء
(`/appointments`, `/billing/invoices`, `/billing/payments`):

| الحالة | السلوك |
|---|---|
| أول طلب | ينفَّذ وتُخزَّن الاستجابة |
| نفس المفتاح + نفس المحتوى | تُعاد **نفس** الاستجابة (بدون إنشاء ثانٍ) |
| نفس المفتاح + محتوى مختلف | `409 IDEMPOTENCY_KEY_REUSED` |
| نفس المفتاح والطلب الأول ما زال قيد التنفيذ | `409 CONFLICT` («الطلب جارٍ تنفيذه») |

مدة الاحتفاظ بالمفتاح: 24 ساعة.

## 5. المسارات (ملخص)

### المصادقة
| الطريقة | المسار | الوصف |
|---|---|---|
| GET | `/auth/session` | ملف الجلسة (الدور + الصلاحيات) |
| GET | `/auth/whoami` | نفس الغرض (اسم مستعار) |
| POST | `/auth/logout` | إنهاء الجلسة الحالية فورًا |
| POST | `/auth/password` | تغيير كلمة المرور (يلغي بقية الجلسات) |
| POST | `/auth/dev-login` | **تطوير فقط** (local/test فقط) — يعيد `{token, expires_in_minutes, staff}` |

### المواعيد
| GET | `/appointments` | قائمة مع تصفية وترقيم |
| POST | `/appointments` | حجز (409 عند التعارض) |
| GET | `/appointments/{id}` | تفاصيل |
| PATCH | `/appointments/{id}` | تعديل سبب الزيارة/الملاحظات |
| POST | `/appointments/{id}/status` | تغيير الحالة |
| POST | `/appointments/{id}/reschedule` | إعادة جدولة ذرّية |
| POST | `/appointments/{id}/cancel` | إلغاء |
| GET | `/appointments/day/{YYYY-MM-DD}?doctor_staff_id=` | جدول اليوم + الأوقات المتاحة |

### الأطباء والجداول
| GET | `/doctors` | دليل الأطباء (اسم + تخصص) |
| GET/PUT | `/doctors/{id}/schedule` | ساعات العمل الأسبوعية |
| GET/POST | `/doctors/{id}/breaks` | الاستراحات |
| GET/POST | `/doctors/leaves` | الإجازات |
| GET | `/doctors/{id}/slots?day=YYYY-MM-DD` | الأوقات المتاحة |

### المرضى
| GET/POST | `/patients` | قائمة/تسجيل (الريسبشن فقط للإنشاء) |
| GET/PATCH | `/patients/{id}` | عرض/تعديل |
| POST | `/patients/{id}/deactivate` | سحب السجل (**يلزم سبب**) |

### الزيارات (الطبيب فقط)
| GET/POST | `/visits` | قائمة/فتح سجل زيارة |
| GET/PATCH | `/visits/{id}` | قراءة/تعديل |
| POST | `/visits/{id}/complete` | تأكيد اكتمال الكشف |
| POST | `/visits/grants` | منح صلاحية اطلاع |
| GET | `/visits/grants/list` | قائمة التفويضات |
| POST | `/visits/grants/{id}/revoke` | إلغاء التفويض |

### الفواتير والتحصيل
| GET/POST | `/billing/services` | قائمة الخدمات / إضافة |
| PATCH/DELETE | `/billing/services/{id}` | تعديل / تعطيل |
| GET/POST | `/billing/invoices` | الفواتير (كاملة) / إصدار |
| GET | `/billing/invoices/totals` | **إجماليات فقط** (للريسبشن) |
| GET | `/billing/invoices/{id}` | التفاصيل (إجماليات فقط للريسبشن) |
| POST | `/billing/invoices/{id}/void` | إلغاء موثّق |
| POST | `/billing/invoices/{id}/payments` | تحصيل دفعة |
| GET/POST | `/billing/payments` | قائمة / تسجيل دفعة |
| POST | `/billing/payments/{id}/void` | إلغاء دفعة |

### المصروفات (صاحب العيادة)
| GET/POST | `/expenses` | قائمة / تسجيل |
| GET/POST | `/expenses/categories` | التصنيفات |
| POST | `/expenses/{id}/void` | إلغاء موثّق |

### التقارير
| GET | `/reports/weekly?start&end&days` | التقرير الأسبوعي |
| GET | `/reports/doctors` | أداء الأطباء |
| GET | `/reports/schedule` | الجداول |

### الإدارة
| GET/POST | `/staff` | الموظفون / إنشاء حساب |
| PATCH | `/staff/{id}` | تعديل |
| POST | `/staff/{id}/disable` \| `/enable` | تعطيل/تفعيل |
| POST | `/staff/{id}/reset-password` | كلمة مرور مؤقتة |
| GET | `/staff/{id}/sessions` | الجلسات |
| POST | `/staff/{id}/sessions/revoke` | إنهاء كل الجلسات |
| GET | `/audit` | سجل التدقيق (صاحب العيادة) |
| GET | `/meta/clinic` | المنطقة الزمنية والعملة والصلاحيات |
| GET | `/health`, `/health/ready` | فحص الخدمة |

## 6. أمثلة

### حجز موعد ناجح
```http
POST /api/v1/appointments
{"doctor_staff_id":"…","patient_id":"…","starts_at":"2026-01-05T10:00:00+02:00","visit_reason":"كشفية"}
```
```json
{"id":"…","doctor_staff_id":"…","patient_id":"…","starts_at":"2026-01-05T08:00:00Z",
 "ends_at":"2026-01-05T08:30:00Z","status":"pending","patient":{"id":"…","full_name":"…","phone":"…"},
 "doctor_name":"د. …","reschedule_count":0,"version":1}
```

### تعارض حجز
```http
POST /api/v1/appointments  → 409
```
```json
{"error":{"code":"APPOINTMENT_CONFLICT","message":"هذا الموعد لم يعد متاحًا. اختر موعدًا آخر.",
 "details":{"conflicting_starts_at":"2026-01-05T08:00:00Z","conflicting_ends_at":"2026-01-05T08:30:00Z"},
 "request_id":"…"}}
```

### تسجيل دفعة (تسجيل جهاز دفع)
```http
POST /api/v1/billing/payments
{"invoice_id":"…","amount":"150.00","method":"visa","reference":"POS-9931"}
```

### التقرير الأسبوعي (مقتطف)
```json
{"period":{"start":"2026-10-14","end":"2026-10-20","timezone":"Africa/Cairo","days":7},
 "currency":"EGP","invoiced_total":"4000.00","collected_total":"3250.00",
 "expenses_total":"1200.00","net_result":"2050.00","outstanding_total":"750.00",
 "invoice_count":11,"payment_count":9,"expense_count":4,"appointment_count":63,
 "collected_by_method":{"cash":"2250.00","visa":"1000.00"},
 "daily":[{"date":"2026-10-14","invoiced_total":"0.00","collected_total":"450.00","expenses_total":"0.00","net_result":"450.00","appointments":9}],
 "notes":"صافي النتيجة = المتحصلات ناقص المصروفات المسجلة. هذا مؤشر تشغيلي وليس ربحًا محاسبيًا نهائيًا."}
```
