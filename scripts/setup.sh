#!/usr/bin/env bash
# =============================================================================
# تهيئة المشروع وتشغيله محليًا من الصفر
# =============================================================================
# الاستخدام:
#   ./scripts/setup.sh          # تهيئة + تثبيت الاعتماديات + ترحيلات + تشغيل
#   ./scripts/setup.sh --no-run # تهيئة فقط بدون تشغيل الخوادم
#
# ما يفعله:
#   1) ينشئ backend/.env و frontend/.env.local من النماذج (إن لم يكونا موجودين).
#   2) ينشئ بيئة Python ويثبّت الاعتماديات.
#   3) ينشئ قاعدة بيانات PostgreSQL محلية ويطبّق الترحيلات.
#   4) يزرع بيانات تطوير اختيارية.
#   5) يشغّل الخلفية والواجهة.
# =============================================================================
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"
RUN=1
PG_PORT="${CLINIC_PG_PORT:-55432}"
PG_DATA="${CLINIC_PG_DATA:-$BACKEND/.pgdata}"
PG_DB="clinic_dev"

for arg in "$@"; do
  case "$arg" in
    --no-run) RUN=0 ;;
    -h|--help) sed -n '2,18p' "$0"; exit 0 ;;
    *) echo "خيار غير معروف: $arg"; exit 2 ;;
  esac
done

step() { printf '\n\033[1m> %s\033[0m\n' "$1"; }
info() { printf '   %s\n' "$1"; }

step "1/6) ملفات الإعدادات"
if [[ -f "$BACKEND/.env" ]]; then
  info "backend/.env موجود — لن يُمس."
else
  cp "$BACKEND/.env.example" "$BACKEND/.env"
  info "أُنشئ backend/.env من .env.example"
fi
if [[ -f "$FRONTEND/.env.local" ]]; then
  info "frontend/.env.local موجود — لن يُمس."
else
  cp "$FRONTEND/.env.example" "$FRONTEND/.env.local"
  info "أُنشئ frontend/.env.local من .env.example"
fi
# اضبط رابط قاعدة البيانات على قاعدة التطوير المحلية
if grep -q "^DATABASE_URL=" "$BACKEND/.env"; then
  python3 - "$BACKEND/.env" "$PG_PORT" "$PG_DB" <<'PY'
import re, sys
path, port, db = sys.argv[1], sys.argv[2], sys.argv[3]
text = open(path, encoding="utf-8").read()
text = re.sub(
    r"^DATABASE_URL=.*$",
    f"DATABASE_URL=postgresql+asyncpg://postgres:clinic_local@127.0.0.1:{port}/{db}",
    text, flags=re.M,
)
open(path, "w", encoding="utf-8").write(text)
PY
  info "تم ضبط DATABASE_URL على قاعدة التطوير المحلية."
fi

step "2/6) بيئة Python والاعتماديات"
if [[ ! -x "$BACKEND/.venv/bin/python" ]]; then
  python3 -m venv "$BACKEND/.venv"
  info "أُنشئت backend/.venv"
fi
"$BACKEND/.venv/bin/pip" install --quiet --upgrade pip
"$BACKEND/.venv/bin/pip" install --quiet -e "$BACKEND[dev]"
info "تم تثبيت اعتماديات الخلفية (مثبّتة بإصدارات دقيقة)."

step "3/6) اعتماديات الواجهة"
if [[ ! -d "$FRONTEND/node_modules" ]]; then
  (cd "$FRONTEND" && npm install --no-audit --no-fund)
  info "تم تثبيت اعتماديات الواجهة."
else
  info "node_modules موجود — تم تخطي التثبيت."
fi

step "4/6) قاعدة البيانات المحلية"
if command -v python3 >/dev/null; then
  (cd "$BACKEND" && "$BACKEND/.venv/bin/python" scripts/local_pg.py start --port "$PG_PORT" --data-dir "$PG_DATA") \
    | tail -1
  info "قاعدة البيانات المحلية على المنفذ $PG_PORT (قاعدة $PG_DB)."
fi

step "5/6) الترحيلات وبيانات التطوير"
(cd "$BACKEND" && "$BACKEND/.venv/bin/alembic" upgrade head) | tail -2
if [[ -z "${SKIP_SEED:-}" ]]; then
  (cd "$BACKEND" && ALLOW_DEV_SEED=1 "$BACKEND/.venv/bin/python" scripts/seed_dev_data.py) | tail -5
fi

if [[ $RUN -eq 0 ]]; then
  step "اكتمل التهيئة (بدون تشغيل)."
  exit 0
fi

step "6/6) تشغيل الخلفية والواجهة"
(cd "$BACKEND" && "$BACKEND/.venv/bin/uvicorn" app.main:app --host 127.0.0.1 --port 8000 --reload) \
  > "$BACKEND/uvicorn.log" 2>&1 &
BACK_PID=$!
info "الخلفية: http://127.0.0.1:8000  (توثيق: /docs)  — السجل: backend/uvicorn.log"

(cd "$FRONTEND" && npm run dev -- --port 3000) > "$FRONTEND/next-dev.log" 2>&1 &
FRONT_PID=$!
info "الواجهة: http://127.0.0.1:3000  (السجل: frontend/next-dev.log)"

cat <<EOF

$(printf '\033[32m\033[1mالنظام يعمل.\033[0m')
  الواجهة   : http://127.0.0.1:3000
  الـ API   : http://127.0.0.1:8000/docs
  دخول تطوير: owner@clinic.local / reception@clinic.local / doctor1@clinic.local

  للإيقاف: kill $BACK_PID $FRONT_PID
EOF
wait
