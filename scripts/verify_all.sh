#!/usr/bin/env bash
# =============================================================================
# فحص شامل للمشروع: تنسيق، أنواع، اختبارات، أمان، أسرار
# =============================================================================
# الاستخدام:  ./scripts/verify_all.sh
# المخرجات: رمز 0 = كل الفحوص ناجحة، 1 = فشل فحص واحد على الأقل.
# =============================================================================
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"
VENV="$BACKEND/.venv"
FAILED=0

step() { printf '\n\033[1m> %s\033[0m\n' "$1"; }
ok()   { printf '\033[32m[OK] %s\033[0m\n' "$1"; }
warn() { printf '\033[33m[!] %s\033[0m\n' "$1"; }
fail() { printf '\033[31m[X] %s\033[0m\n' "$1"; FAILED=1; }

if [[ ! -x "$VENV/bin/python" ]]; then
  echo "بيئة Python غير موجودة. أنشئها:"
  echo "  cd backend && python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'"
  exit 1
fi

step "1/6 — تنسيق وأخطاء شائعة (ruff)"
if (cd "$BACKEND" && "$VENV/bin/ruff" check app tests migrations scripts --output-format=concise); then
  ok "ruff"
else
  fail "ruff"
fi

step "2/6 — فحص الأنواع (mypy)"
if (cd "$BACKEND" && "$VENV/bin/mypy" app); then
  ok "mypy"
else
  fail "mypy"
fi

step "3/6 — الاختبارات (pytest، على PostgreSQL حقيقي)"
if (cd "$BACKEND" && "$VENV/bin/python" -m pytest -q); then
  ok "pytest"
else
  fail "pytest"
fi

step "4/6 — ثغرات اعتماديات الخلفية (pip-audit)"
# نفحص ملف التثبيت المثبَّت (requirements.lock.txt) لا البيئة، فتُفحص
#exactly الحزم التي ستُثبَّت على الخادم.
if (cd "$BACKEND" && "$VENV/bin/pip-audit" -r requirements.lock.txt --strict); then
  ok "pip-audit"
else
  fail "pip-audit"
fi

step "5/6 — فحص الأسرار"
if (cd "$BACKEND" && "$VENV/bin/python" scripts/check_secrets.py); then
  ok "فحص الأسرار"
else
  fail "فحص الأسرار"
fi

step "6/6 — الواجهة (typecheck + build + tests + audit)"
if [[ -d "$FRONTEND/node_modules" ]]; then
  if (cd "$FRONTEND" && npx tsc --noEmit); then ok "tsc"; else fail "tsc"; fi
  if (cd "$FRONTEND" && npm run lint >/dev/null 2>&1); then ok "eslint"; else fail "eslint"; fi
  if (cd "$FRONTEND" && npm run build >/dev/null 2>&1); then ok "next build"; else fail "next build"; fi
  if (cd "$FRONTEND" && npm test --silent >/dev/null 2>&1); then ok "frontend tests"; else fail "frontend tests"; fi
  # البوابة تعتمد على اعتماديات الإنتاج فقط؛ اعتماديات التطوير تُعرَض كتحذير.
  if (cd "$FRONTEND" && npm audit --omit=dev --audit-level=moderate >/dev/null 2>&1); then
    ok "npm audit (اعتماديات الإنتاج)"
  else
    fail "npm audit (اعتماديات الإنتاج)"
  fi
  if (cd "$FRONTEND" && npm audit --audit-level=high >/dev/null 2>&1); then
    ok "npm audit (اعتماديات التطوير)"
  else
    warn "ثغرات في اعتماديات التطوير فقط (braces عبر eslint): لا إصلاح متاح من upstream، وهي خارج حزمة الإنتاج."
  fi
else
  warn "تم تخطي فحص الواجهة: node_modules غير موجود (npm install)"
fi

printf '\n'
if [[ $FAILED -eq 0 ]]; then
  printf '\033[32m\033[1mكل الفحوص ناجحة.\033[0m\n'
else
  printf '\033[31m\033[1mهناك فحص فاشل — راجع أعلاه.\033[0m\n'
fi
exit $FAILED
