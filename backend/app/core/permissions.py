"""Authorization model: operations and data classes.

Two independent layers enforce access:

1. **Operation level** — :class:`Permission` + :data:`ROLE_PERMISSIONS`.
   Checked in the API layer (dependency) *and* re-checked in the service layer.
2. **Data level** — the *projection* of each record for the caller's role.
   The clinic owner, for example, is allowed to see that a patient exists and
   what a doctor earned, but never the diagnosis. Projections live in
   ``app/schemas`` and are applied in the service layer.

Row-level isolation (a doctor seeing *their own* patients only) is enforced a
third time by PostgreSQL Row Level Security — see ``migrations/`` for the
policies.

The matrix below is the single source of truth; ``docs/PERMISSIONS.md`` is
generated from it by ``scripts/generate_permissions_doc.py``.
"""

from __future__ import annotations

from enum import StrEnum

from app.models.enums import StaffRole


class Permission(StrEnum):
    """Operation-level capabilities."""

    # Patients
    PATIENT_READ = "patient:read"                 # demographics (scoped by role)
    PATIENT_READ_MEDICAL = "patient:read_medical"  # medical content of own patients
    PATIENT_CREATE = "patient:create"
    PATIENT_UPDATE = "patient:update"
    PATIENT_DEACTIVATE = "patient:deactivate"

    # Appointments
    APPOINTMENT_READ = "appointment:read"          # full schedule (all doctors)
    APPOINTMENT_READ_OWN = "appointment:read_own"  # own schedule only
    APPOINTMENT_CREATE = "appointment:create"
    APPOINTMENT_UPDATE_STATUS = "appointment:update_status"
    APPOINTMENT_CANCEL = "appointment:cancel"
    APPOINTMENT_RESCHEDULE = "appointment:reschedule"
    APPOINTMENT_AVAILABILITY = "appointment:availability"

    # Visits / medical file
    VISIT_READ_OWN = "visit:read_own"
    VISIT_READ_GRANTED = "visit:read_granted"
    VISIT_WRITE = "visit:write"
    VISIT_COMPLETE = "visit:complete"
    VISIT_GRANT_ACCESS = "visit:grant_access"

    # Billing
    INVOICE_READ = "invoice:read"                 # all invoices (financial)
    INVOICE_READ_OWN_WORK = "invoice:read_own_work"
    INVOICE_READ_TOTALS = "invoice:read_totals"   # total / paid / remaining only
    INVOICE_CREATE = "invoice:create"
    INVOICE_VOID = "invoice:void"
    PAYMENT_READ = "payment:read"
    PAYMENT_CREATE = "payment:create"
    PAYMENT_VOID = "payment:void"

    # Expenses
    EXPENSE_READ = "expense:read"
    EXPENSE_CREATE = "expense:create"
    EXPENSE_VOID = "expense:void"

    # Reports
    REPORT_SCHEDULE = "report:schedule"
    REPORT_FINANCIAL = "report:financial"
    REPORT_WEEKLY = "report:weekly"

    # Administration
    SERVICE_READ = "service:read"
    SERVICE_MANAGE = "service:manage"
    STAFF_READ = "staff:read"
    STAFF_CREATE = "staff:create"
    STAFF_UPDATE = "staff:update"
    STAFF_DISABLE = "staff:disable"
    DOCTOR_SCHEDULE_READ = "doctor_schedule:read"
    DOCTOR_SCHEDULE_MANAGE = "doctor_schedule:manage"
    AUDIT_READ = "audit:read"


DOCTOR_PERMISSIONS: frozenset[Permission] = frozenset(
    {
        Permission.PATIENT_READ,
        Permission.PATIENT_READ_MEDICAL,
        Permission.APPOINTMENT_READ_OWN,
        Permission.APPOINTMENT_UPDATE_STATUS,
        Permission.APPOINTMENT_AVAILABILITY,
        Permission.VISIT_READ_OWN,
        Permission.VISIT_READ_GRANTED,
        Permission.VISIT_WRITE,
        Permission.VISIT_COMPLETE,
        Permission.VISIT_GRANT_ACCESS,
        Permission.INVOICE_READ_OWN_WORK,
        Permission.REPORT_SCHEDULE,
        Permission.SERVICE_READ,
        Permission.DOCTOR_SCHEDULE_READ,
    }
)

OWNER_PERMISSIONS: frozenset[Permission] = frozenset(
    {
        Permission.PATIENT_READ,
        Permission.PATIENT_DEACTIVATE,
        Permission.APPOINTMENT_READ,
        Permission.APPOINTMENT_CREATE,
        Permission.APPOINTMENT_UPDATE_STATUS,
        Permission.APPOINTMENT_CANCEL,
        Permission.APPOINTMENT_RESCHEDULE,
        Permission.APPOINTMENT_AVAILABILITY,
        Permission.INVOICE_READ,
        Permission.INVOICE_CREATE,
        Permission.INVOICE_VOID,
        Permission.PAYMENT_READ,
        Permission.PAYMENT_CREATE,
        Permission.PAYMENT_VOID,
        Permission.EXPENSE_READ,
        Permission.EXPENSE_CREATE,
        Permission.EXPENSE_VOID,
        Permission.REPORT_SCHEDULE,
        Permission.REPORT_FINANCIAL,
        Permission.REPORT_WEEKLY,
        Permission.SERVICE_READ,
        Permission.SERVICE_MANAGE,
        Permission.STAFF_READ,
        Permission.STAFF_CREATE,
        Permission.STAFF_UPDATE,
        Permission.STAFF_DISABLE,
        Permission.DOCTOR_SCHEDULE_READ,
        Permission.DOCTOR_SCHEDULE_MANAGE,
        Permission.AUDIT_READ,
    }
)

RECEPTIONIST_PERMISSIONS: frozenset[Permission] = frozenset(
    {
        Permission.PATIENT_READ,
        Permission.PATIENT_CREATE,
        Permission.PATIENT_UPDATE,
        Permission.APPOINTMENT_READ,
        Permission.APPOINTMENT_CREATE,
        Permission.APPOINTMENT_UPDATE_STATUS,
        Permission.APPOINTMENT_CANCEL,
        Permission.APPOINTMENT_RESCHEDULE,
        Permission.APPOINTMENT_AVAILABILITY,
        Permission.INVOICE_READ_TOTALS,
        Permission.INVOICE_CREATE,
        Permission.PAYMENT_READ,
        Permission.PAYMENT_CREATE,
        Permission.REPORT_SCHEDULE,
        Permission.SERVICE_READ,
        Permission.DOCTOR_SCHEDULE_READ,
    }
)

ROLE_PERMISSIONS: dict[StaffRole, frozenset[Permission]] = {
    StaffRole.DOCTOR: DOCTOR_PERMISSIONS,
    StaffRole.OWNER: OWNER_PERMISSIONS,
    StaffRole.RECEPTIONIST: RECEPTIONIST_PERMISSIONS,
}


def has_permission(role: StaffRole, permission: Permission) -> bool:
    return permission in ROLE_PERMISSIONS.get(role, frozenset())


def permissions_for(role: StaffRole) -> frozenset[Permission]:
    return ROLE_PERMISSIONS.get(role, frozenset())


#: Data classes that carry clinical content. Only a doctor may ever read them.
CLINICAL_DATA_CLASSES = frozenset(
    {
        "visit.diagnosis",
        "visit.treatment",
        "visit.notes",
        "visit.chief_complaint",
        "visit.vitals",
    }
)
