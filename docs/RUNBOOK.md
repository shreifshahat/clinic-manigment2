# دليل التشغيل والإعداد والنشر

## 1. المتطلبات

| المكوّن | الحد الأدنى | ملاحظة |
|---|---|---|
| Python | 3.12 | طُوِّر واختُبر على 3.14 |
| Node.js | 20 LTS | طُوِّر على 22 |
| PostgreSQL | 14+ | Supabaseprovides 15/16/17؛ الاختبارات على 18 |
| حساب Supabase | مشروع واحد | للمصادقة + قاعدة البيانات |

لا حاجة إلى Docker ولا إلى تثبيت PostgreSQL محليًا: سكربت
`backend/scripts/local_pg.py` يشغّل PostgreSQL حقيقيًا من ملفات مُضمّنة.

## 2. التشغيل المحلي (من الصفر)

### 2.1 الخلفية

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env          # ثم عدّل القيم

# قاعدة بيانات محلية
python scripts/local_pg.py start --port 55432 --data-dir .pgdata
# DATABASE_URL=postgresql+asyncpg://postgres:clinic_local@127.0.0.1:55432/postgres

alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

- التوثيق: <http://localhost:8000/docs>
- فحص الجاهزية: `curl http://localhost:8000/health/ready`

### 2.2 بيانات تطوير (اختياري)

```bash
ALLOW_DEV_SEED=1 python scripts/seed_dev_data.py
```
السكربت يرفض العمل في الإنتاج أو إذا كانت هناك حسابات بالفعل. البيانات
اصطناعية (أسماء وأرقام خيالية) وهي للتطوير فقط.

### 2.3 الواجهة

```bash
cd frontend
npm install
cp .env.example .env.local     # NEXT_PUBLIC_API_BASE_URL + Supabase
npm run dev                    # http://localhost:3000
```

## 3. الإعداد على Supabase

1. أنشئ مشروعًا على Supabase.
2. **Database → Connection string** (URI): انسخ الرابط.
3. أنشئ دور التطبيق:
   ```bash
   psql "$SUPABASE_ADMIN_URL" -f backend/scripts/create_db_role.sql
   ```
   (استبدل كلمة المرور داخل الملف، أو نفّذ الأوامر من SQL Editor).
4. `DATABASE_URL=postgresql+asyncpg://clinic_app:<password>@db.<ref>.supabase.co:5432/postgres`
5. شغّل الترحيلات:
   ```bash
   cd backend && DATABASE_URL="postgresql+asyncpg://postgres:<pass>@db.<ref>.supabase.co:5432/postgres" alembic upgrade head
   ```
   (الترحيلات تحتاج دور المالك).
6. من **Authentication → Providers → Email**: فعّل الدخول بالبريد/كلمة المرور
   (أو استخدم magic link). عطّل «Signup» العام بعد إنشاء أول حساب.
7. أضف `SUPABASE_URL` و`SUPABASE_ANON_KEY` و`SUPABASE_SERVICE_ROLE_KEY`.
8. **أنشئ أول حساب صاحب عيادة** (انظر `scripts/bootstrap_owner.py`).

## 4. متغيرات البيئة

| المتغير | مطلوب | مثال | ملاحظة |
|---|---|---|---|
| `ENV` | ✅ | `production` | `local`/`test`/`staging`/`production` |
| `DATABASE_URL` | ✅ | `postgresql+asyncpg://clinic_app:…@db.<ref>.supabase.co:5432/postgres` | **لا** يُستخدم `service_role` هنا |
| `SUPABASE_URL` | ✅ (إنتاج) | `https://<ref>.supabase.co` | |
| `SUPABASE_ANON_KEY` | ✅ (واجهة) | `eyJ…` | آمن في المتصفح |
| `SUPABASE_SERVICE_ROLE_KEY` | ✅ (إنتاج) | `eyJ…` | **سريّ** — الخلفية فقط |
| `CORS_ORIGINS` | ✅ | `https://clinic.example.com` | بدون `*` في الإنتاج |
| `CLINIC_TIMEZONE` | | `Africa/Cairo` | |
| `CLINIC_CURRENCY` | | `EGP` | |
| `WEEK_START_WEEKDAY` | | `6` | 1=الاثنين..6=السبت..7=الأحد |
| `ACCESS_TOKEN_TTL_MINUTES` | | `30` | |
| `RATE_LIMIT_PER_MINUTE` | | `120` | لكل IP، لكل عملية |
| `LOG_LEVEL` | | `INFO` | |
| `DEV_AUTH_ENABLED` | | `false` | **يجب** أن يكون `false` في الإنتاج |
| `DEV_AUTH_SECRET` | | — | للتطوير فقط، 32 حرفًا فأكثر |

## 5. النشر

### 5.1 الخلفية

خياران:

**أ) منصة حاويات / VM:**
```bash
docker build -t clinic-api .
docker run -d --name clinic-api -p 8000:8000 --env-file .env clinic-api
```

**ب) خادم Application:**
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2 --proxy-headers --forwarded-allow-ips='<proxy>'
```
- `--workers N` ملاحظة: حد الطلبات في الذاكرة يتضاعف مع N (انظر `SECURITY.md` R1).
- شغّل خلف عاكس يوفّر TLS (Caddy/nginx/Cloudflare).
- مرّر `X-Forwarded-For` بشكل صحيح لأن `request.client.host` يُستخدم للـ rate limit.

### 5.2 الواجهة (Next.js)

```bash
cd frontend
npm ci && npm run build
npm run start          # أو انشر على Vercel
```
- `NEXT_PUBLIC_API_BASE_URL=https://api.clinic.example.com/api/v1`
- `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- أضف نطاق الواجهة إلى `CORS_ORIGINS` في الخلفية.

### 5.3 قائمة تحقق النشر
راجع `SECURITY.md` §6.

## 6. المراقبة

| المؤشر | الطريقة | الإجراء |
|---|---|---|
| أخطاء 5xx | سجل JSON `level=ERROR` | تنبيه |
| تكرار `409 APPOINTMENT_CONFLICT` | نفس السجل | طبيعي (نشاط عالٍ)؛ ارتفاع مفاجئ → تحقق من أجهزة الحجز |
| `401 SESSION_REVOKED` متكرر | نفس السجل | تحقق من إعادة تعيين كلمات المرور |
| `429 RATE_LIMITED` | نفس السجل | تحقق من تكرار الطلبات |
| تعطل Health | `/health/ready` | تنبيه فوري |
| نمو قاعدة البيانات | حجم التخزين | مراجعة الحذف/الأرشفة دوريًا |

## 7. الصيانة الدورية

| المهمة | التكرار | الأمر/الإجراء |
|---|---|---|
| تنظيف جلسات منتهية | أسبوعي | `python backend/scripts/cleanup_sessions.py` (يحذف الجلسات ومفاتيح التكرار المنتهية) |
| تنظيف مفاتيح Idempotency منتهية | أسبوعي | `delete from idempotency_keys where expires_at < now()` |
| مراجعة سجل التدقيق | أسبوعي | `GET /api/v1/audit` أو SQL |
| تدقيق الاعتماديات | شهري | `pip-audit` + `npm audit` |
| ترحيل قاعدة البيانات | قبل كل نشر | `alembic upgrade head` |

## 8. النسخ الاحتياطي والاستعادة

### 8.1 ما الذي يُنسخ

| البيانات | الأهمية | التكرار المقترح |
|---|---|---|
| قاعدة البيانات (كل الجداول) | حرجة | يومي + WAL المستمر |
| إعدادات FastAPI/`.env` | حرجة (مفاتيح) | في مدير أسرار + نسخة مشفّرة منفصلة |
| كود الواجهة والخلفية | عالية | مع كل إصدار (git) |

### 8.2 النسخ من Supabase

Supabase Pro provides **Point-in-Time Recovery (PITR)** (ن retention حتى 7 أيام
لـ14 يومًا حسب الخطة) + **Daily backups** (7 أيام). هذه هي الطبقة الأولى.

الطبقة الثانية (خارج Supabase) — نسخة مستقلة:

```bash
# نسخة كاملة (pg_dump مخصّص بصيغة custom)
pg_dump --format=custom --no-owner --file clinic_$(date +%F).dump "$DATABASE_URL"

# نسخة السجلات فقط
pg_dump --data-only --table='patients' --table='visits' --table='invoices' \
        --table='payments' --table='expenses' --file clinic_data_$(date +%F).dump "$DATABASE_URL"
```

جدولة يومية (cron):

```cron
0 2 * * * /usr/bin/pg_dump --format=custom --no-owner --file /var/backups/clinic/clinic_$(date +\%F).dump "$DATABASE_URL" && /usr/bin/gzip /var/backups/clinic/clinic_$(date +\%F).dump
```

- **التشفير**: استخدم `age` أو `gpg` للنسخ قبل مغادرة الخادم.
- **الاحتفاظ**: يومي 14 يومًا، أسبوعي 8 أسابيع، شهري 12 شهرًا (يُحذف الأقدم تلقائيًا).
- **موقع مختلف**: لا تُخزَّن النسخ على نفس حساب Supabase.

### 8.3 اختبار الاستعادة (إلزامي كل ربع)

التمرين مُؤتمت بالكامل:

```bash
cd backend
./scripts/restore_drill.sh --source "$DATABASE_URL" --host <host> --port <port>
```

يقوم بـ: التقاط نسخة → إنشاء قاعدة فارغة → الاستعادة → **مقارنة 7 جداول + مجموع
الفواتير** → طباعة النتيجة (PASS/FAIL) ومدة الاستعادة (RTO).

**نقاط التحقق:**
1. عدد السجلات في الجداول الأساسية متساوية.
2. مجموع مبالغ الفواتير غير الملغاة متساوٍ.
3. سجل التدقيق موجود ومطابق.
4. **التطبيق يعمل على القاعدة المستعادة** (تشغيل الـ API واختبار حجز تجريبي).
5. مدة الاستعادة (RTO) **≤ 4 ساعات**، ومدة recoveries ≤ 24 ساعة (RPO).

> **حالة المشروع:** تم تنفيذ التمرين **محليًا وبنجاح** عبر
> `backend/scripts/restore_drill.sh` (المقارنة على 7 جداول + مجموع الفواتير).
> **المتبقّي:** تشغيله على نسخة Supabase الفعلية — يحتاج `DATABASE_URL` لمشروعك.

## 9. استعادة من نسخة

```bash
# 1) إيقاف التطبيق (حتى لا يكتب على القاعدة أثناء الاستعادة)
systemctl stop clinic-api
# 2) استعادة
dropdb clinic_production && createdb clinic_production
pg_restore --no-owner --dbname clinic_production /var/backups/clinic/clinic_2026-01-05.dump
# 3) إعادة تشغيل التطبيق والتحقق
systemctl start clinic-api && curl -fsS https://api.clinic.example.com/health/ready
```

بعد الاستعادة: تحقّق من `alembic_version` مقابل آخر ترحيل منشور، وقدّم
`alembic upgrade head` إن لزم الأمر.

## 10. حدود التشغيل

- النظام مصمَّم لم数百 المعاملات في اليوم؛ وليس بديلًا عن نظام HIS كامل.
- لا يطبّق قواعد تأمين ولا فوترة ضريبية ولا تكامل实验室.
- النسخ الاحتياطي والاستعادة مسؤولية مشغّل البنية التحتية، والخطة هنا إرشادية.
