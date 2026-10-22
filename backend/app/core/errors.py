"""Unified error contract for the whole API.

Every error response has the same shape so the frontend can branch on a stable
machine-readable ``code`` instead of parsing human text:

    {
      "error": {
        "code": "APPOINTMENT_CONFLICT",
        "message": "هذا الموعد لم يعد متاحًا. اختر موعدًا آخر.",
        "details": {},
        "request_id": "b2f3...."
      }
    }

Rules enforced here:
* ``code`` is a stable constant (never a free-text message).
* ``message`` is Arabic, human readable, and never contains secrets, SQL,
  stack traces, patient data or medical content.
* ``details`` carries *safe* structured context (e.g. conflicting window) and is
  scrubbed by the caller before it is attached.
* ``request_id`` is echoed so a user can quote it to support and we can find
  the matching server log line.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class ErrorCode:
    """Stable, machine-readable error codes (part of the public API contract)."""

    VALIDATION_ERROR = "VALIDATION_ERROR"
    AUTHENTICATION_REQUIRED = "AUTHENTICATION_REQUIRED"
    INVALID_TOKEN = "INVALID_TOKEN"  # noqa: S105 - an error code, not a secret
    SESSION_REVOKED = "SESSION_REVOKED"
    ACCOUNT_DISABLED = "ACCOUNT_DISABLED"
    PASSWORD_CHANGE_REQUIRED = "PASSWORD_CHANGE_REQUIRED"  # noqa: S105 - an error code
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    METHOD_NOT_ALLOWED = "METHOD_NOT_ALLOWED"

    APPOINTMENT_CONFLICT = "APPOINTMENT_CONFLICT"
    SLOT_UNAVAILABLE = "SLOT_UNAVAILABLE"
    OUTSIDE_WORKING_HOURS = "OUTSIDE_WORKING_HOURS"
    INVALID_STATE_TRANSITION = "INVALID_STATE_TRANSITION"
    DUPLICATE_BOOKING = "DUPLICATE_BOOKING"
    RESCHEDULE_CONFLICT = "RESCHEDULE_CONFLICT"

    INVOICE_NOT_FOUND = "INVOICE_NOT_FOUND"
    INVOICE_ALREADY_VOID = "INVOICE_ALREADY_VOID"
    PAYMENT_EXCEEDS_REMAINING = "PAYMENT_EXCEEDS_REMAINING"
    PAYMENT_ALREADY_VOID = "PAYMENT_ALREADY_VOID"
    EXPENSE_ALREADY_VOID = "EXPENSE_ALREADY_VOID"

    IDEMPOTENCY_KEY_REUSED = "IDEMPOTENCY_KEY_REUSED"
    RATE_LIMITED = "RATE_LIMITED"
    CONFLICT = "CONFLICT"
    INTERNAL_ERROR = "INTERNAL_ERROR"


#: Default human-readable Arabic messages per code. Services may override the
#: message when more context helps the user, but the code stays stable.
DEFAULT_MESSAGES: dict[str, str] = {
    ErrorCode.VALIDATION_ERROR: "البيانات المُرسلة غير صالحة. راجع الحقول المميزة.",
    ErrorCode.AUTHENTICATION_REQUIRED: "يجب تسجيل الدخول للمتابعة.",
    ErrorCode.INVALID_TOKEN: "جلسة الدخول غير صالحة. سجّل الدخول من جديد.",
    ErrorCode.SESSION_REVOKED: "انتهت صلاحية الجلسة. سجّل الدخول من جديد.",
    ErrorCode.ACCOUNT_DISABLED: "الحساب غير مُفعّل. راجع صاحب العيادة.",
    ErrorCode.PASSWORD_CHANGE_REQUIRED: "يجب تغيير كلمة المرور المؤقتة قبل متابعة العمل.",
    ErrorCode.FORBIDDEN: "لا تملك صلاحية تنفيذ هذه العملية.",
    ErrorCode.NOT_FOUND: "العنصر المطلوب غير موجود.",
    ErrorCode.METHOD_NOT_ALLOWED: "طريقة الطلب غير مدعومة لهذا المسار.",
    ErrorCode.APPOINTMENT_CONFLICT: "هذا الموعد لم يعد متاحًا. اختر موعدًا آخر.",
    ErrorCode.SLOT_UNAVAILABLE: "الوقت المطلوب غير متاح للطبيب.",
    ErrorCode.OUTSIDE_WORKING_HOURS: "الوقت المطلوب خارج ساعات عمل الطبيب.",
    ErrorCode.INVALID_STATE_TRANSITION: "لا يمكن نقل الحالة إلى هذه القيمة.",
    ErrorCode.DUPLICATE_BOOKING: "يوجد حجز مطابق لهذا الموعد بالفعل.",
    ErrorCode.RESCHEDULE_CONFLICT: "الوقت الجديد متعارض. لم يُعدَّل الحجز الأصلي.",
    ErrorCode.INVOICE_NOT_FOUND: "الفاتورة غير موجودة.",
    ErrorCode.INVOICE_ALREADY_VOID: "الفاتورة مُلغاة مسبقًا.",
    ErrorCode.PAYMENT_EXCEEDS_REMAINING: "المبلغ المدفوع يتجاوز المتبقي على الفاتورة.",
    ErrorCode.PAYMENT_ALREADY_VOID: "عملية الدفع مُلغاة مسبقًا.",
    ErrorCode.EXPENSE_ALREADY_VOID: "المصروف مُلغى مسبقًا.",
    ErrorCode.IDEMPOTENCY_KEY_REUSED: "مفتاح التكرار استُخدم مسبقًا لطلب مختلف.",
    ErrorCode.RATE_LIMITED: "عدد المحاولات كبير. انتظر قليلًا ثم أعد المحاولة.",
    ErrorCode.CONFLICT: "تعارض في العملية الحالية.",
    ErrorCode.INTERNAL_ERROR: "حدث خطأ غير متوقع. تم تسجيل المشكلة وسنتابعها.",
}


class AppError(Exception):
    """Base class for all *expected* (business) failures.

    Raising an ``AppError`` anywhere in the service layer is enough for the API
    to return a well-formed error envelope. Nothing internal leaks: the
    exception message is used only for the server log, never for the client.
    """

    code: str = ErrorCode.INTERNAL_ERROR
    http_status: int = status.HTTP_500_INTERNAL_SERVER_ERROR

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        details: dict[str, Any] | None = None,
        http_status: int | None = None,
        log_message: str | None = None,
    ) -> None:
        self.code = code or self.code
        self.http_status = http_status or self.http_status
        self.message = message or DEFAULT_MESSAGES.get(self.code, "حدث خطأ غير متوقع.")
        self.details = details or {}
        self.log_message = log_message or self.message
        super().__init__(self.log_message)


class AuthenticationError(AppError):
    code = ErrorCode.AUTHENTICATION_REQUIRED
    http_status = status.HTTP_401_UNAUTHORIZED


class InvalidTokenError(AppError):
    code = ErrorCode.INVALID_TOKEN
    http_status = status.HTTP_401_UNAUTHORIZED


class SessionRevokedError(AppError):
    code = ErrorCode.SESSION_REVOKED
    http_status = status.HTTP_401_UNAUTHORIZED


class AccountDisabledError(AppError):
    code = ErrorCode.ACCOUNT_DISABLED
    http_status = status.HTTP_403_FORBIDDEN


class ForbiddenError(AppError):
    code = ErrorCode.FORBIDDEN
    http_status = status.HTTP_403_FORBIDDEN


class PasswordChangeRequiredError(AppError):
    """The account still uses its temporary password."""

    code = ErrorCode.PASSWORD_CHANGE_REQUIRED
    http_status = status.HTTP_403_FORBIDDEN


class NotFoundError(AppError):
    code = ErrorCode.NOT_FOUND
    http_status = status.HTTP_404_NOT_FOUND


class ConflictError(AppError):
    code = ErrorCode.CONFLICT
    http_status = status.HTTP_409_CONFLICT


class AppointmentConflictError(ConflictError):
    code = ErrorCode.APPOINTMENT_CONFLICT


class RescheduleConflictError(ConflictError):
    code = ErrorCode.RESCHEDULE_CONFLICT


class ValidationBusinessError(AppError):
    """Business-rule validation failure (as opposed to schema validation)."""

    code = ErrorCode.VALIDATION_ERROR
    http_status = 422


class IdempotencyConflictError(ConflictError):
    code = ErrorCode.IDEMPOTENCY_KEY_REUSED


class RateLimitedError(AppError):
    code = ErrorCode.RATE_LIMITED
    http_status = status.HTTP_429_TOO_MANY_REQUESTS


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "")


def error_payload(
    request: Request,
    *,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
            "request_id": _request_id(request),
        }
    }


def _safe_validation_details(exc: RequestValidationError) -> dict[str, Any]:
    """Convert pydantic errors into a compact, non-sensitive structure."""
    fields: list[dict[str, Any]] = []
    for err in exc.errors():
        loc = [str(part) for part in err.get("loc", []) if part not in ("body", "query")]
        fields.append(
            {
                "field": ".".join(loc) or "body",
                "issue": err.get("type", "invalid"),
                "message": err.get("msg", "قيمة غير صالحة"),
            }
        )
    return {"fields": fields}


def register_exception_handlers(app: FastAPI) -> None:
    """Attach the uniform error envelope to every failure mode."""

    @app.exception_handler(AppError)
    async def _app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.http_status,
            content=error_payload(
                request,
                code=exc.code,
                message=exc.message,
                details=exc.details,
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=error_payload(
                request,
                code=ErrorCode.VALIDATION_ERROR,
                message=DEFAULT_MESSAGES[ErrorCode.VALIDATION_ERROR],
                details=_safe_validation_details(exc),
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        code = {
            status.HTTP_401_UNAUTHORIZED: ErrorCode.AUTHENTICATION_REQUIRED,
            status.HTTP_403_FORBIDDEN: ErrorCode.FORBIDDEN,
            status.HTTP_404_NOT_FOUND: ErrorCode.NOT_FOUND,
            status.HTTP_405_METHOD_NOT_ALLOWED: ErrorCode.METHOD_NOT_ALLOWED,
        }.get(exc.status_code, ErrorCode.INTERNAL_ERROR)
        message = (
            exc.detail
            if isinstance(exc.detail, str)
            else DEFAULT_MESSAGES.get(code, "حدث خطأ غير متوقع.")
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=error_payload(request, code=code, message=message),
        )

    @app.exception_handler(Exception)
    async def _unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
        # The traceback is logged with the request id; the client only gets a
        # generic message plus the request id for support.
        import logging

        logging.getLogger("clinic.api").exception(
            "unhandled error", extra={"request_id": _request_id(request)}
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_payload(
                request,
                code=ErrorCode.INTERNAL_ERROR,
                message=DEFAULT_MESSAGES[ErrorCode.INTERNAL_ERROR],
            ),
        )
