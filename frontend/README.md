# واجهة نظام إدارة العيادة — Frontend

Next.js 15 (App Router) · TypeScript (strict) · Tailwind CSS v4 · TanStack Query ·
عربية بالكامل واتجاه من اليمين إلى اليسار.

الواجهة **تعرض فقط**؛ الفرض الحقيقي للصلاحيات في الخادم (مصادقة + صلاحيات +
Row Level Security). إخفاء عناصر التنقل راحة للمستخدم لا ضابط أمني.

## التشغيل

```bash
npm install
cp .env.example .env.local     # ثم عدّل القيم
npm run dev                    # http://localhost:3000
```

### متغيّرات البيئة

| المتغيّر | مطلوب | الوصف |
|---|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | ✅ | عنوان الـ API، مثل `http://localhost:8000/api/v1` |
| `NEXT_PUBLIC_SUPABASE_URL` | ✅ | رابط مشروع Supabase (للمصادقة) |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | ✅ | المفتاح العام `anon` — آمن في المتصفح |
| `NEXT_PUBLIC_ENABLE_DEV_LOGIN` | | `true` لتفعيل شاشة الدخول في وضع التطوير فقط |

> **لا تضع `SUPABASE_SERVICE_ROLE_KEY` في أي متغيّر يبدأ بـ`NEXT_PUBLIC_`** — كل
> متغيّر بهذا البادئة يُحقن في حزمة المتصفح.

### التشغيل بدون Supabase (تطوير)

مع `NEXT_PUBLIC_ENABLE_DEV_LOGIN=true` **و** خادم يعمل بـ
`DEV_AUTH_ENABLED=true` (و `ENV=local`)، تظهر شاشة دخول تطلب بريد موظف
 موجود فقط (مثل `owner@clinic.local` بعد `seed_dev_data.py`).
الخادم يرفض هذا المسار في الإنتاج.

## الأوامر

| الأمر | الوظيفة |
|---|---|
| `npm run dev` | خادم التطوير |
| `npm run build` | بناء الإنتاج (`next build`) |
| `npm run start` | تشغيل بناء الإنتاج |
| `npm run typecheck` | فحص الأنواع (`tsc --noEmit`) |
| `npm run lint` | ESLint |
| `npm test` | اختبارات Vitest |

## البنية

```
src/
├── app/
│   ├── layout.tsx           # <html lang="ar" dir="rtl"> + المزوّدات
│   ├── page.tsx             # توجيه إلى /dashboard أو /login
│   ├── login/page.tsx       # تسجيل الدخول
│   ├── error.tsx            # حدّ أخطاء على مستوى الصفحة
│   ├── not-found.tsx        # 404
│   └── (app)/               # صفحات محمية بجلسة
│       ├── layout.tsx       # يحوّل إلى /login عند انتهاء الجلسة
│       └── <route>/page.tsx
├── components/
│   ├── ui/                  # مكتبة UI صغيرة (button, card, table, states…)
│   └── *-panel.tsx          # لوحات الأدوار
├── lib/
│   ├── api.ts               # عميل HTTP موحّد + غلاف الأخطاء
│   ├── api-types.ts         # أنواع مطابقة لمخططات Pydantic
│   ├── endpoints.ts         # نقاط النهاية typed
│   ├── errors.ts            # عقد الخطأ + كشف التعارض
│   ├── format.ts            # المال والتواريخ (Intl + المنطقة الزمنية للعيادة)
│   ├── idempotency.ts       # توليد Idempotency-Key
│   ├── permissions.ts       # خريطة التنقل حسب الصلاحيات
│   ├── auth.tsx             # Supabase Auth (متصفح فقط)
│   ├── clinic.tsx           # جلسة العيادة + الصلاحيات + العملة/المنطقة الزمنية
│   └── dev-auth.ts          # دخول التطوير (معطّل افتراضيًا)
└── test/setup.ts
```

## الصفحات والأدوار

| المسار | صاحب العيادة | الطبيب | الريسبشن |
|---|:--:|:--:|:--:|
| `/dashboard` | ملخص مالي + حركة اليوم | مواعيد اليوم | مواعيد اليوم |
| `/appointments` | ✅ | مواعيده | ✅ |
| `/booking` | ✅ | — | ✅ |
| `/patients` | ✅ (بلا هاتف) | مرضاه | ✅ |
| `/visits` | — | ✅ | — |
| `/invoices` | ✅ (ببنودها) | فواتير عمله | — |
| `/collection` | — | — | ✅ (إجماليات فقط) |
| `/expenses` | ✅ | — | — |
| `/reports/weekly` | ✅ | — | — |
| `/reports/doctors` | ✅ | — | — |
| `/schedules` | ✅ | قراءة | قراءة |
| `/staff` | ✅ | — | — |
| `/grants` | ✅ | ✅ | — |
| `/audit` | ✅ | — | — |
| `/account` | ✅ | ✅ | ✅ (تغيير كلمة المرور) |

## سلوكيات مهمة

- **منع التكرار**: كل عملية إنشاء (موعد/فاتورة/دفعة) ترسل `Idempotency-Key`،
  والأزرار تُعطَّل أثناء التنفيذ (`loading`).
- **تعارض الحجز**: `409 APPOINTMENT_CONFLICT` / `RESCHEDULE_CONFLICT` →
  رسالة واضحة + **تحديث قائمة الأوقات المتاحة** + اقتراح بدائل.
- **خارج ساعات العمل**: `422 OUTSIDE_WORKING_HOURS` → عرض ساعات عمل الطبيب.
- **لا بيانات وهمية**: كل قائمة تعرض حالة فارغة صريحة عند غياب البيانات.
- **الأخطاء**: رسالة الخادم العربية كما هي + `request_id` لل.support.
- **المبالغ**: نصوص عشرية تُعرض بالأرقام العربية، دون أي حساب بفاصلة عائمة.
- **التواريخ**: كل التوادم UTC، والعرض لمنطقة العيادة من `GET /meta/clinic`.

## الاختبارات

```bash
npm test
```

تغطي: معالجة أخطاء الـ API (الغلاف، عدم تسريب التفاصيل، كشف التعارض)،
تنسيق المال والتواريخ بالمنطقة الزمنية، إخفاء عناصر التنقل حسب الدور،
وحالات العرض (تحميل/فارغة/خطأ/نجاح) + لوحة تحكم صاحب العيادة.
