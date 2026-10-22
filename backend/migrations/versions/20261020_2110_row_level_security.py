"""row level security, conflict constraints and access grants

Revision ID: 20261020_2110_rls
Revises: d6ba924b2952
Create Date: 2026-10-20 21:10:00

This migration is the **database-level** half of the authorization model:

* a GiST exclusion constraint that makes overlapping bookings impossible even
  for a manual ``INSERT``;
* Row Level Security policies on every table, so the API role can only see
  the rows its role is allowed to see;
* explicit ``GRANT``/``REVOKE`` statements: the application role gets DML on
  the tables it needs, and the *direct* PostgREST path (``anon`` /
  ``authenticated``) is closed — all data must pass through the API, which is
  where field-level minimisation lives.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "20261020_2110_rls"
down_revision: str | None = "d6ba924b2952"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# ---------------------------------------------------------------------------
# Extensions & sequence
# ---------------------------------------------------------------------------
def upgrade() -> None:
    op.execute("create extension if not exists btree_gist")
    # gen_random_uuid() is built into PostgreSQL 13+, so pgcrypto is not needed.
    op.execute(
        "create sequence if not exists invoice_number_seq as bigint start with 1 "
        "increment by 1 no cycle"
    )

    # -----------------------------------------------------------------------
    # Conflict prevention (final authority)
    # -----------------------------------------------------------------------
    op.execute(
        """
        alter table appointments
            add constraint no_overlap_per_doctor
            exclude using gist (
                doctor_staff_id with =,
                tstzrange(starts_at, ends_at) with &&
            )
            where (status in ('pending', 'confirmed', 'in_progress'))
        """
    )
    op.execute(
        """
        create unique index uq_appointments_active_patient_slot
            on appointments (doctor_staff_id, patient_id, starts_at)
            where status in ('pending', 'confirmed', 'in_progress')
        """
    )

    # -----------------------------------------------------------------------
    # Compatibility shim for auth.uid() outside Supabase
    # -----------------------------------------------------------------------
    op.execute(
        """
        do $do$
        begin
            if not exists (select 1 from pg_namespace where nspname = 'auth') then
                execute 'create schema auth';
            end if;
            if to_regprocedure('auth.uid()') is null then
                execute 'create or replace function auth.uid() returns uuid '
                        'language sql stable as $fn$ select null::uuid $fn$';
            end if;
        end
        $do$;
        """
    )

    # -----------------------------------------------------------------------
    # Helper functions
    # -----------------------------------------------------------------------
    op.execute(
        """
        create or replace function app_current_staff_id() returns uuid
        language plpgsql stable security definer
        set search_path = public, pg_temp
        as $fn$
        declare
            v uuid;
        begin
            begin
                v := nullif(current_setting('app.user_id', true), '')::uuid;
            exception when others then
                v := null;
            end;
            if v is not null then
                return v;
            end if;
            return (select s.id from public.staff s where s.auth_user_id = auth.uid());
        end
        $fn$
        """
    )
    op.execute(
        """
        create or replace function app_current_staff_role() returns text
        language plpgsql stable security definer
        set search_path = public, pg_temp
        as $fn$
        declare
            v text;
        begin
            v := nullif(current_setting('app.role', true), '');
            if v is not null then
                return v;
            end if;
            return (select s.role from public.staff s where s.auth_user_id = auth.uid());
        end
        $fn$
        """
    )
    op.execute(
        """
        create or replace function app_staff_by_auth_id(p_auth_user_id uuid)
        returns table (
            id uuid,
            role text,
            full_name text,
            email text,
            is_active boolean,
            must_change_password boolean
        )
        language sql stable security definer
        set search_path = public, pg_temp
        as $fn$
            select s.id, s.role, s.full_name, s.email, s.is_active, s.must_change_password
              from public.staff s
             where s.auth_user_id = p_auth_user_id
        $fn$
        """
    )
    op.execute(
        """
        create or replace function app_staff_by_email(p_email text)
        returns table (
            id uuid,
            auth_user_id uuid,
            role text,
            full_name text,
            email text,
            is_active boolean
        )
        language sql stable security definer
        set search_path = public, pg_temp
        as $fn$
            select s.id, s.auth_user_id, s.role, s.full_name, s.email, s.is_active
              from public.staff s
             where lower(s.email) = lower(p_email)
        $fn$
        """
    )
    op.execute(
        """
        create or replace function app_has_visit_access(p_visit uuid) returns boolean
        language sql stable security definer
        set search_path = public, pg_temp
        as $fn$
            select exists (
                select 1
                  from public.visit_access_grants g
                 where g.visit_id = p_visit
                   and g.granted_doctor_staff_id = app_current_staff_id()
                   and g.revoked_at is null
                   and (g.expires_at is null or g.expires_at > now())
            )
        $fn$
        """
    )
    op.execute(
        """
        create or replace function app_owns_visit(p_visit uuid) returns boolean
        language sql stable security definer
        set search_path = public, pg_temp
        as $fn$
            select exists (
                select 1 from public.visits v
                 where v.id = p_visit
                   and v.doctor_staff_id = app_current_staff_id()
            )
        $fn$
        """
    )
    op.execute(
        """
        create or replace function app_doctor_treats_patient(p_patient uuid) returns boolean
        language sql stable security definer
        set search_path = public, pg_temp
        as $fn$
            select exists (
                select 1
                  from public.appointments a
                 where a.patient_id = p_patient
                   and a.doctor_staff_id = app_current_staff_id()
            )
        $fn$
        """
    )
    op.execute(
        """
        create or replace function app_doctor_directory()
        returns table (
            id uuid,
            full_name text,
            specialty text,
            role text,
            is_active boolean
        )
        language sql stable security definer
        set search_path = public, pg_temp
        as $fn$
            select s.id,
                   s.full_name,
                   coalesce(d.specialty, ''),
                   s.role,
                   s.is_active
              from public.staff s
              left join public.doctors d on d.staff_id = s.id
             where s.role = 'doctor'
             order by s.full_name
        $fn$
        """
    )
    op.execute(
        """
        create or replace function app_is_active_doctor(p_staff_id uuid) returns boolean
        language sql stable security definer
        set search_path = public, pg_temp
        as $fn$
            select exists (
                select 1 from public.staff s
                 where s.id = p_staff_id
                   and s.role = 'doctor'
                   and s.is_active
            )
        $fn$
        """
    )
    op.execute(
        """
        create or replace function app_can_read_invoice(p_invoice uuid) returns boolean
        language sql stable security definer
        set search_path = public, pg_temp
        as $fn$
            select exists (
                select 1
                  from public.invoices i
                 where i.id = p_invoice
                   and (
                       app_current_staff_role() in ('owner', 'receptionist')
                       or (
                           app_current_staff_role() = 'doctor'
                           and (
                               exists (
                                   select 1 from public.appointments a
                                    where a.id = i.appointment_id
                                      and a.doctor_staff_id = app_current_staff_id()
                               )
                               or exists (
                                   select 1 from public.visits v
                                    where v.id = i.visit_id
                                      and v.doctor_staff_id = app_current_staff_id()
                               )
                           )
                       )
                   )
            )
        $fn$
        """
    )

    # -----------------------------------------------------------------------
    # Enable RLS on every table
    # -----------------------------------------------------------------------
    tables = [
        "staff",
        "doctors",
        "doctor_working_hours",
        "doctor_breaks",
        "doctor_leaves",
        "staff_sessions",
        "patients",
        "appointments",
        "visits",
        "visit_access_grants",
        "services",
        "invoices",
        "invoice_items",
        "payments",
        "expense_categories",
        "expenses",
        "audit_log",
        "idempotency_keys",
    ]
    for table in tables:
        op.execute(f"alter table {table} enable row level security")
    # NOTE: deliberately *not* using FORCE ROW LEVEL SECURITY. The helper
    # functions below are SECURITY DEFINER and owned by the table owner; with
    # FORCE enabled they would themselves be filtered by the policies and the
    # authentication handshake would break. The application connects with a
    # dedicated non-owner role (``clinic_app``), for which RLS always applies.

    # -----------------------------------------------------------------------
    # Policies
    # -----------------------------------------------------------------------
    policies: list[tuple[str, str, str]] = [
        # --- staff --------------------------------------------------------
        (
            "staff_select",
            "staff",
            "for select using (id = app_current_staff_id() "
            "or app_current_staff_role() = 'owner')",
        ),
        (
            "staff_insert",
            "staff",
            "for insert with check (app_current_staff_role() = 'owner')",
        ),
        (
            "staff_update",
            "staff",
            "for update using (app_current_staff_role() = 'owner') "
            "with check (app_current_staff_role() = 'owner')",
        ),
        # --- doctors ------------------------------------------------------
        (
            "doctors_select",
            "doctors",
            "for select using (app_current_staff_id() is not null)",
        ),
        (
            "doctors_insert",
            "doctors",
            "for insert with check (app_current_staff_role() = 'owner')",
        ),
        (
            "doctors_update",
            "doctors",
            "for update using (app_current_staff_role() = 'owner') "
            "with check (app_current_staff_role() = 'owner')",
        ),
        # --- schedule -----------------------------------------------------
        (
            "doctor_working_hours_select",
            "doctor_working_hours",
            "for select using (app_current_staff_id() is not null)",
        ),
        (
            "doctor_working_hours_write",
            "doctor_working_hours",
            "for all using (app_current_staff_role() = 'owner') "
            "with check (app_current_staff_role() = 'owner')",
        ),
        (
            "doctor_breaks_select",
            "doctor_breaks",
            "for select using (app_current_staff_id() is not null)",
        ),
        (
            "doctor_breaks_write",
            "doctor_breaks",
            "for all using (app_current_staff_role() = 'owner') "
            "with check (app_current_staff_role() = 'owner')",
        ),
        (
            "doctor_leaves_select",
            "doctor_leaves",
            "for select using (app_current_staff_id() is not null)",
        ),
        (
            "doctor_leaves_write",
            "doctor_leaves",
            "for all using (app_current_staff_role() = 'owner') "
            "with check (app_current_staff_role() = 'owner')",
        ),
        # --- sessions -----------------------------------------------------
        (
            "staff_sessions_select",
            "staff_sessions",
            "for select using (staff_id = app_current_staff_id() "
            "or app_current_staff_role() = 'owner')",
        ),
        (
            "staff_sessions_insert",
            "staff_sessions",
            "for insert with check (staff_id = app_current_staff_id())",
        ),
        (
            "staff_sessions_update",
            "staff_sessions",
            "for update using (staff_id = app_current_staff_id() "
            "or app_current_staff_role() = 'owner')",
        ),
        # --- patients -----------------------------------------------------
        (
            "patients_select",
            "patients",
            "for select using (app_current_staff_role() in ('owner', 'receptionist') "
            "or (app_current_staff_role() = 'doctor' and app_doctor_treats_patient(id)))",
        ),
        (
            "patients_insert",
            "patients",
            "for insert with check (app_current_staff_role() in ('owner', 'receptionist'))",
        ),
        (
            "patients_update",
            "patients",
            "for update using (app_current_staff_role() in ('owner', 'receptionist')) "
            "with check (app_current_staff_role() in ('owner', 'receptionist'))",
        ),
        # --- appointments -------------------------------------------------
        (
            "appointments_select",
            "appointments",
            "for select using (app_current_staff_role() in ('owner', 'receptionist') "
            "or (app_current_staff_role() = 'doctor' "
            "and doctor_staff_id = app_current_staff_id()))",
        ),
        (
            "appointments_insert",
            "appointments",
            "for insert with check (app_current_staff_role() in ('owner', 'receptionist'))",
        ),
        (
            "appointments_update",
            "appointments",
            "for update using (app_current_staff_role() in ('owner', 'receptionist') "
            "or (app_current_staff_role() = 'doctor' "
            "and doctor_staff_id = app_current_staff_id())) "
            "with check (app_current_staff_role() in ('owner', 'receptionist') "
            "or (app_current_staff_role() = 'doctor' "
            "and doctor_staff_id = app_current_staff_id()))",
        ),
        # --- visits (clinical) --------------------------------------------
        (
            "visits_select",
            "visits",
            "for select using (app_current_staff_role() = 'doctor' "
            "and (doctor_staff_id = app_current_staff_id() "
            "or app_has_visit_access(id)))",
        ),
        (
            "visits_insert",
            "visits",
            "for insert with check (app_current_staff_role() = 'doctor' "
            "and doctor_staff_id = app_current_staff_id())",
        ),
        (
            "visits_update",
            "visits",
            "for update using (app_current_staff_role() = 'doctor' "
            "and doctor_staff_id = app_current_staff_id()) "
            "with check (app_current_staff_role() = 'doctor' "
            "and doctor_staff_id = app_current_staff_id())",
        ),
        # --- visit access grants ------------------------------------------
        (
            "visit_access_grants_select",
            "visit_access_grants",
            "for select using (granted_doctor_staff_id = app_current_staff_id() "
            "or granted_by_staff_id = app_current_staff_id() "
            "or app_current_staff_role() = 'owner')",
        ),
        (
            "visit_access_grants_insert",
            "visit_access_grants",
            "for insert with check (app_current_staff_role() = 'owner' "
            "or (app_current_staff_role() = 'doctor' and app_owns_visit(visit_id)))",
        ),
        (
            "visit_access_grants_update",
            "visit_access_grants",
            "for update using (app_current_staff_role() = 'owner' "
            "or granted_by_staff_id = app_current_staff_id())",
        ),
        # --- services -----------------------------------------------------
        (
            "services_select",
            "services",
            "for select using (app_current_staff_id() is not null)",
        ),
        (
            "services_write",
            "services",
            "for all using (app_current_staff_role() = 'owner') "
            "with check (app_current_staff_role() = 'owner')",
        ),
        # --- invoices -----------------------------------------------------
        (
            "invoices_select",
            "invoices",
            "for select using (app_current_staff_role() in ('owner', 'receptionist') "
            "or (app_current_staff_role() = 'doctor' and app_can_read_invoice(id)))",
        ),
        (
            "invoices_insert",
            "invoices",
            "for insert with check (app_current_staff_role() in ('owner', 'receptionist'))",
        ),
        (
            "invoices_update",
            "invoices",
            "for update using (app_current_staff_role() in ('owner', 'receptionist')) "
            "with check (app_current_staff_role() in ('owner', 'receptionist'))",
        ),
        # --- invoice items ------------------------------------------------
        (
            "invoice_items_select",
            "invoice_items",
            "for select using (app_can_read_invoice(invoice_id))",
        ),
        (
            "invoice_items_insert",
            "invoice_items",
            "for insert with check (app_current_staff_role() in ('owner', 'receptionist'))",
        ),
        # --- payments -----------------------------------------------------
        (
            "payments_select",
            "payments",
            "for select using (app_current_staff_role() in ('owner', 'receptionist') "
            "or (app_current_staff_role() = 'doctor' "
            "and app_can_read_invoice(invoice_id)))",
        ),
        (
            "payments_insert",
            "payments",
            "for insert with check (app_current_staff_role() in ('owner', 'receptionist'))",
        ),
        (
            "payments_update",
            "payments",
            "for update using (app_current_staff_role() = 'owner') "
            "with check (app_current_staff_role() = 'owner')",
        ),
        # --- expenses (owner only) ----------------------------------------
        (
            "expense_categories_select",
            "expense_categories",
            "for select using (app_current_staff_role() = 'owner')",
        ),
        (
            "expense_categories_write",
            "expense_categories",
            "for all using (app_current_staff_role() = 'owner') "
            "with check (app_current_staff_role() = 'owner')",
        ),
        (
            "expenses_select",
            "expenses",
            "for select using (app_current_staff_role() = 'owner')",
        ),
        (
            "expenses_insert",
            "expenses",
            "for insert with check (app_current_staff_role() = 'owner')",
        ),
        (
            "expenses_update",
            "expenses",
            "for update using (app_current_staff_role() = 'owner') "
            "with check (app_current_staff_role() = 'owner')",
        ),
        # --- audit log (append only) --------------------------------------
        (
            "audit_log_insert",
            "audit_log",
            "for insert with check (app_current_staff_id() is not null)",
        ),
        (
            "audit_log_select",
            "audit_log",
            "for select using (app_current_staff_role() = 'owner')",
        ),
        # --- idempotency --------------------------------------------------
        (
            "idempotency_keys_all",
            "idempotency_keys",
            "for all using (staff_id = app_current_staff_id()) "
            "with check (staff_id = app_current_staff_id())",
        ),
        # --- settings -----------------------------------------------------
    ]

    for name, table, clause in policies:
        op.execute(f"drop policy if exists {name} on {table}")
        op.execute(f"create policy {name} on {table} {clause}")

    # -----------------------------------------------------------------------
    # Immutability of posted financial records
    #
    # The application layer already never edits a posted amount; these
    # triggers make that a database guarantee as well: only the clinic owner
    # may change the financial fields, and everyone else may only touch the
    # status / void columns.
    # -----------------------------------------------------------------------
    op.execute(
        """
        create or replace function app_guard_invoice_update() returns trigger
        language plpgsql as $fn$
        begin
            if coalesce(app_current_staff_role(), '') <> 'owner' then
                if new.total is distinct from old.total
                   or new.invoice_number is distinct from old.invoice_number
                   or new.issued_at is distinct from old.issued_at
                   or new.patient_id is distinct from old.patient_id
                   or new.currency is distinct from old.currency
                   or new.appointment_id is distinct from old.appointment_id
                   or new.visit_id is distinct from old.visit_id then
                    raise exception 'financial fields of an invoice may only be changed by the owner'
                        using errcode = '42501';
                end if;
            end if;
            return new;
        end
        $fn$
        """
    )
    op.execute(
        """
        create or replace function app_guard_invoice_item_update() returns trigger
        language plpgsql as $fn$
        begin
            if coalesce(app_current_staff_role(), '') <> 'owner' then
                if new.quantity is distinct from old.quantity
                   or new.unit_price is distinct from old.unit_price
                   or new.line_total is distinct from old.line_total
                   or new.description is distinct from old.description then
                    raise exception 'invoice lines may only be changed by the owner'
                        using errcode = '42501';
                end if;
            end if;
            return new;
        end
        $fn$
        """
    )
    op.execute(
        """
        create or replace function app_guard_payment_update() returns trigger
        language plpgsql as $fn$
        begin
            if coalesce(app_current_staff_role(), '') <> 'owner' then
                if new.amount is distinct from old.amount
                   or new.method is distinct from old.method
                   or new.invoice_id is distinct from old.invoice_id
                   or new.received_at is distinct from old.received_at then
                    raise exception 'a recorded payment may only be cancelled, not edited'
                        using errcode = '42501';
                end if;
            end if;
            return new;
        end
        $fn$
        """
    )
    op.execute(
        """
        create or replace function app_guard_expense_update() returns trigger
        language plpgsql as $fn$
        begin
            if coalesce(app_current_staff_role(), '') <> 'owner' then
                if new.amount is distinct from old.amount
                   or new.description is distinct from old.description
                   or new.category_id is distinct from old.category_id
                   or new.incurred_at is distinct from old.incurred_at then
                    raise exception 'a recorded expense may only be cancelled, not edited'
                        using errcode = '42501';
                end if;
            end if;
            return new;
        end
        $fn$
        """
    )
    for table, function in (
        ("invoices", "app_guard_invoice_update"),
        ("invoice_items", "app_guard_invoice_item_update"),
        ("payments", "app_guard_payment_update"),
        ("expenses", "app_guard_expense_update"),
    ):
        op.execute(f"drop trigger if exists {function}_trg on {table}")
        op.execute(
            f"create trigger {function}_trg before update on {table} "
            f"for each row execute function {function}()"
        )

    # -----------------------------------------------------------------------
    # Grants
    # -----------------------------------------------------------------------
    op.execute(
        """
        do $do$
        begin
            if exists (select 1 from pg_roles where rolname = 'clinic_app') then
                grant usage on schema public to clinic_app;
                grant select, insert, update on all tables in schema public to clinic_app;
                grant delete on doctor_working_hours, doctor_breaks, doctor_leaves
                    to clinic_app;
                grant usage, select on all sequences in schema public to clinic_app;
                grant execute on all functions in schema public to clinic_app;
                if exists (select 1 from pg_namespace where nspname = 'auth') then
                    execute 'grant usage on schema auth to clinic_app';
                    if to_regprocedure('auth.uid()') is not null then
                        execute 'grant execute on function auth.uid() to clinic_app';
                    end if;
                end if;
            end if;

            -- Close the direct PostgREST data path: the browser talks to the
            -- API only. Supabase Auth still works (it uses the auth schema).
            if exists (select 1 from pg_roles where rolname = 'anon') then
                revoke all on all tables in schema public from anon;
                revoke all on all sequences in schema public from anon;
            end if;
            if exists (select 1 from pg_roles where rolname = 'authenticated') then
                revoke all on all tables in schema public from authenticated;
                revoke all on all sequences in schema public from authenticated;
            end if;

            revoke all on all tables in schema public from public;
            revoke all on all sequences in schema public from public;
        end
        $do$;
        """
    )
    op.execute(
        """
        do $do$
        begin
            execute 'alter default privileges in schema public revoke all on tables from public';
            execute 'alter default privileges in schema public revoke all on sequences from public';
            if exists (select 1 from pg_roles where rolname = 'anon') then
                execute 'alter default privileges in schema public revoke all on tables from anon';
            end if;
            if exists (select 1 from pg_roles where rolname = 'authenticated') then
                execute 'alter default privileges in schema public revoke all on tables from authenticated';
            end if;
        end
        $do$;
        """
    )


def downgrade() -> None:
    op.execute("drop sequence if exists invoice_number_seq")
    op.execute("drop index if exists uq_appointments_active_patient_slot")
    op.execute("alter table appointments drop constraint if exists no_overlap_per_doctor")
    for function in (
        "app_guard_expense_update",
        "app_guard_payment_update",
        "app_guard_invoice_item_update",
        "app_guard_invoice_update",
        "app_is_active_doctor",
        "app_doctor_directory",
        "app_can_read_invoice",
        "app_doctor_treats_patient",
        "app_owns_visit",
        "app_has_visit_access",
        "app_staff_by_email",
        "app_staff_by_auth_id",
        "app_current_staff_role",
        "app_current_staff_id",
    ):
        op.execute(f"drop function if exists {function}")
