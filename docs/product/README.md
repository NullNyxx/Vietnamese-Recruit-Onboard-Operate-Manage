# Product Docs

This directory contains Vroom HR product contracts and module specs.

Active backend modules are identity, employee, Gmail, and recruitment. Specs for
attendance, payroll, and self-service remain here as archived reference material
because migration `027_drop_attendance_payroll_tables.py` retired their active
backend tables and routes.

## Update Rule

When behavior changes:

1. Update the affected product doc.
2. Update or create the story packet.
3. Update durable proof status with `scripts/harness story add` or
   `scripts/harness story update`.
4. Record a decision if the change affects architecture, scope, risk, or a
   previously settled product rule.
