# نظام إدارة العيادة — Clinic Management System

نظام داخلي لإدارة عيادة طبية: مواعيد بلا تعارض، ملف طبي محمي، تحصيل
مالي دقيق، وتقرير أسبوعي.

**نطاق النظام:** موظفو العيادة فقط (طبيب / صاحب عيادة / ريسبشن).
**ليس فيه:** بوابة مرضى، استشارات فيديو، محادثات مباشرة، ولا بوابة دفع
إلكترونية.

---

> **📦 حزمة التسليم:** [`DELIVERY.md`](./DELIVERY.md) — ملخص تنفيذي، طريقة التشغيل،
> ما ثُبِت بالاختبار، وما يحتاج قرارًا منك. ابدأ من هنا.

## المحتويات

| المستند | الغرض |
|---|---|
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | التقنيات وأسبابها، بنية المشروع، تدفّق الطلب |
| [`docs/DATABASE.md`](docs/DATABASE.md) | المخطط، قيود منع التعارض، سياسات RLS، الاحتفاظ بالبيانات |
| [`docs/PERMISSIONS.md`](docs/PERMISSIONS.md) | **مصفوفة الصلاحيات** لكل دور (مولّدة من الكود) |
| [`docs/API.md`](docs/API.md) | توثيق الـ API وأكواد الأخطاء |
| [`docs/REPORTS.md`](docs/REPORTS.md) | تعريف كل رقم في التقارير |
| [`docs/SECURITY.md`](docs/SECURITY.md) | الضوابط المطبَّقة والمخاطر المتبقية |
| [`docs/RUNBOOK.md`](docs/RUNBOOK.md) | التشغيل والإعداد والنشر والنسخ الاحتياطي |
| [`docs/USER_GUIDE.md`](docs/USER_GUIDE.md) | دليل استخدام مختصر لكل دور |
| [`docs/TESTING.md`](docs/TESTING.md) | الاختبارات وما تغطيه ونتائجها |
| [`docs/SECURITY_REVIEW.md`](docs/SECURITY_REVIEW.md) | **تقرير المراجعة الأمنية والعيوب** |
| [`docs/DECISIONS.md`](docs/DECISIONS.md) | القرارات والافتراضات والأسئلة المعلّقة |
| [`docs/openapi.json`](docs/openapi.json) | مواصفة OpenAPI المولّدة |

## بنية المشروع

```
clinic-system/
├── backend/     # Python 3.12+ · FastAPI · SQLAlchemy 2 · Alembic · PostgreSQL
├── frontend/    # Next.js 15 (App Router) · TypeScript · Tailwind · RTL
│   ├── src/app/(app)/     # 20 مسارًا محميًا بجلسة
├── docs/        # التوثيق أعلاه
└── scripts/
```

## تشغيل سريع (محلي)

```bash
# 1) الخلفية
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
python scripts/local_pg.py start --port 55432 --data-dir .pgdata
alembic upgrade head
uvicorn app.main:app --reload --port 8000        # → http://localhost:8000/docs

# 2) بيانات تطوير (اختياري)
ALLOW_DEV_SEED=1 python scripts/seed_dev_data.py

# 3) الواجهة
cd ../frontend
npm install && cp .env.example .env.local
npm run dev                                       # → http://localhost:3000
```

## الاختبارات

```bash
cd backend
pytest -q          # 62 اختبارًا على PostgreSQL حقيقي
ruff check app tests migrations scripts
mypy app
pip-audit
python scripts/check_secrets.py

cd ../frontend
npm test           # 34 اختبارًا
npm run typecheck
npm run build
```

أو كل الفحوص دفعة واحدة من جذر المشروع: `./scripts/verify_all.sh`

## مبادئ التصميم

1. **الصلاحيات على الخادم والقاعدة، لا على الأزرار.** ثلاث طبقات: صلاحية
   العملية، صلاحية السطر (RLS)، صلاحية الحقل (إسقاط حسب الدور).
2. **الملف الطبي مغلق.** لا توجد في قاعدة البيانات أي سياسة تسمح لصاحب
   العيادة أو الريسبشن بقراءة `visits` — ولا حتى عدّ الصفوف.
3. **لا تعارض مواعيد، حتى تحت الضغط.** قفل معاملي + قيد `EXCLUDE` في
   PostgreSQL + `Idempotency-Key`.
4. **الأثر المالي لا يُمحى.** الفواتير والمدفوعات والمصروفات تُلغى (مع سبب
   ومن نفّذها) ولا تُعدَّل أو تُحذف.
5. **لا بيانات وهمية في الإنتاج.** البيانات الاصطناعية معزولة في الاختبارات
   وسكربت تطوير يرفض العمل في الإنتاج.
6. **المال بالأرقام العشرية.** `Decimal` + `NUMERIC(14,2)`، ولا `float` أبدًا.
7. **كل خطأ موحّد.** كود ثابت + رسالة عربية + `request_id` للتتبع.

## حالة المشروع

| الجزء | الحالة |
|---|---|
| الخلفية (FastAPI) | ✅ مكتملة — 55 مسارًا، 62 اختبارًا ناجحًا |
| قاعدة البيانات + RLS | ✅ مكتملة — 19 جدولًا، ترحيلات Alembic |
| المصادقة (Supabase Auth) | ✅ مكتملة (يتطلب مشروع Supabase للتشغيل الفعلي) |
| الواجهة (Next.js 15 + RTL) | ✅ مكتملة — 20 مسارًا، 34 اختبارًا، بناء ناجح |
| الاختبارات | ✅ 96 (62 خلفية + 34 واجهة) · ❌ اختبار اختراق مستقل غير منفذ |
| النسخ الاحتياطي | ⚠️ الخطة موثّقة · ❌ اختبار استعادة غير منفذ |

> **انظر `docs/SECURITY_REVIEW.md` لقائمة العيوب المكتشفة قبل الإصلاح.**

## الترخيص والسرية

المشروع يحتوي بيانات صحية. **قبل إدخال أي بيانات مريض حقيقية**:
اعتمد سياسة الاحتفاظ بالبيانات (`docs/DATABASE.md` §7) وتحقق من قائمة
`docs/SECURITY.md` §6.
