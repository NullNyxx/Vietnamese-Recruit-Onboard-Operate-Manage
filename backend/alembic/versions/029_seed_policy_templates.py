"""Seed default policy templates.

Populates the policy_templates table with default rules aligned with
the Vietnamese Labor Code 2019 (Law No. 45/2019/QH14) for attendance,
leave, overtime, and disciplinary domains.

Requirements: 2.1, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9

Revision ID: 029
Revises: 028
Create Date: 2026-06-01
"""

from collections.abc import Sequence
from uuid import uuid4

from alembic import op
from sqlalchemy import text

revision: str = "029"
down_revision: str | None = "028"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _insert_template(
    domain: str,
    rule_id: str,
    name: str,
    description: str,
    rule_condition: str,
    rule_action: str,
    priority: int,
    legal_constraints: str | None = None,
) -> str:
    """Build an INSERT statement for a policy template row."""
    lc = legal_constraints if legal_constraints else "NULL"
    lc_clause = f"'{lc}'" if legal_constraints else "NULL"
    return (
        "INSERT INTO policy_templates "
        "(id, domain, rule_id, name, description, rule_condition, rule_action, "
        "priority, enabled, legal_constraints, created_at, updated_at) VALUES ("
        f"'{uuid4()}', '{domain}', '{rule_id}', '{name}', '{description}', "
        f"'{rule_condition}'::jsonb, '{rule_action}'::jsonb, "
        f"{priority}, true, {lc_clause}::jsonb, now(), now())"
    )


def upgrade() -> None:
    """Seed default policy templates for all four domains."""
    conn = op.get_bind()

    # =========================================================================
    # ATTENDANCE TEMPLATES (Requirement 2.4)
    # =========================================================================

    conn.execute(text(_insert_template(
        domain="attendance",
        rule_id="attendance-late-threshold",
        name="Late Threshold",
        description=(
            "Mark attendance as late when check-in exceeds scheduled start "
            "by more than the configured threshold (default 15 minutes)"
        ),
        rule_condition=(
            '{"field": "minutes_late", "operator": "greater_than", "value": 15}'
        ),
        rule_action=(
            '{"type": "flag", "parameters": {"status": "late", "threshold_minutes": 15}}'
        ),
        priority=100,
    )))

    conn.execute(text(_insert_template(
        domain="attendance",
        rule_id="attendance-early-leave-threshold",
        name="Early Leave Threshold",
        description=(
            "Mark attendance as early leave when check-out precedes scheduled "
            "end by more than the configured threshold (default 15 minutes)"
        ),
        rule_condition=(
            '{"field": "minutes_early", "operator": "greater_than", "value": 15}'
        ),
        rule_action=(
            '{"type": "flag", "parameters": {"status": "early_leave", '
            '"threshold_minutes": 15}}'
        ),
        priority=110,
    )))

    conn.execute(text(_insert_template(
        domain="attendance",
        rule_id="attendance-max-daily-hours",
        name="Maximum Daily Working Hours",
        description=(
            "Maximum regular working hours per day is 8 hours per Article 105 "
            "of the Labor Code 2019"
        ),
        rule_condition=(
            '{"field": "daily_hours", "operator": "greater_than", "value": 8}'
        ),
        rule_action=(
            '{"type": "flag", "parameters": {"status": "exceeded_daily_hours", '
            '"max_hours": 8}}'
        ),
        priority=120,
        legal_constraints='{"min_value": 8, "description": "Article 105 Labor Code 2019"}',
    )))

    conn.execute(text(_insert_template(
        domain="attendance",
        rule_id="attendance-max-weekly-hours",
        name="Maximum Weekly Working Hours",
        description=(
            "Maximum regular working hours per week is 48 hours per Article 105 "
            "of the Labor Code 2019"
        ),
        rule_condition=(
            '{"field": "weekly_hours", "operator": "greater_than", "value": 48}'
        ),
        rule_action=(
            '{"type": "flag", "parameters": {"status": "exceeded_weekly_hours", '
            '"max_hours": 48}}'
        ),
        priority=130,
        legal_constraints='{"min_value": 48, "description": "Article 105 Labor Code 2019"}',
    )))

    conn.execute(text(_insert_template(
        domain="attendance",
        rule_id="attendance-absent-marking",
        name="Absent Marking",
        description=(
            "Mark as absent when no check-in is recorded by the end of the "
            "scheduled shift and no approved leave exists for that date"
        ),
        rule_condition=(
            '{"field": "has_check_in", "operator": "equals", "value": false}'
        ),
        rule_action=(
            '{"type": "flag", "parameters": {"status": "absent", '
            '"requires_no_approved_leave": true}}'
        ),
        priority=140,
    )))

    # =========================================================================
    # LEAVE TEMPLATES (Requirement 2.5)
    # =========================================================================

    conn.execute(text(_insert_template(
        domain="leave",
        rule_id="leave-annual-entitlement",
        name="Annual Leave Entitlement",
        description=(
            "Base annual leave entitlement of 12 working days per year "
            "per Article 113 of the Labor Code 2019"
        ),
        rule_condition=(
            '{"field": "leave_type", "operator": "equals", "value": "annual"}'
        ),
        rule_action=(
            '{"type": "calculate", "parameters": {"entitlement_days": 12, '
            '"leave_type": "annual"}}'
        ),
        priority=200,
        legal_constraints=(
            '{"min_value": 12, "description": "Article 113 Labor Code 2019 - '
            'minimum 12 days annual leave"}'
        ),
    )))

    conn.execute(text(_insert_template(
        domain="leave",
        rule_id="leave-seniority-bonus",
        name="Seniority Bonus",
        description=(
            "Additional 1 day of annual leave per 5 years of continuous "
            "service per Article 113 of the Labor Code 2019"
        ),
        rule_condition=(
            '{"field": "years_of_service", "operator": "greater_than_or_equal", '
            '"value": 5}'
        ),
        rule_action=(
            '{"type": "calculate", "parameters": {"bonus_days_per_5_years": 1, '
            '"calculation": "floor(years_of_service / 5)"}}'
        ),
        priority=210,
        legal_constraints=(
            '{"min_value": 1, "description": "Article 113 Labor Code 2019 - '
            'minimum 1 day per 5 years seniority"}'
        ),
    )))

    conn.execute(text(_insert_template(
        domain="leave",
        rule_id="leave-sick-entitlement",
        name="Sick Leave Entitlement",
        description=(
            "Sick leave entitlement of 30 days per year for employees with "
            "normal working conditions per Article 26 of Social Insurance Law"
        ),
        rule_condition=(
            '{"field": "leave_type", "operator": "equals", "value": "sick"}'
        ),
        rule_action=(
            '{"type": "calculate", "parameters": {"entitlement_days": 30, '
            '"leave_type": "sick", "requires_medical_certificate": true}}'
        ),
        priority=220,
        legal_constraints=(
            '{"min_value": 30, "description": "Article 26 Social Insurance Law - '
            'minimum 30 days sick leave for normal conditions"}'
        ),
    )))

    conn.execute(text(_insert_template(
        domain="leave",
        rule_id="leave-maternity-entitlement",
        name="Maternity Leave Entitlement",
        description=(
            "Maternity leave of 6 months per Article 139 of the Labor Code 2019"
        ),
        rule_condition=(
            '{"field": "leave_type", "operator": "equals", "value": "maternity"}'
        ),
        rule_action=(
            '{"type": "calculate", "parameters": {"entitlement_months": 6, '
            '"leave_type": "maternity"}}'
        ),
        priority=230,
        legal_constraints=(
            '{"min_value": 6, "unit": "months", '
            '"description": "Article 139 Labor Code 2019 - minimum 6 months maternity"}'
        ),
    )))

    conn.execute(text(_insert_template(
        domain="leave",
        rule_id="leave-wedding-entitlement",
        name="Wedding Leave Entitlement",
        description=(
            "Wedding leave of 3 days per Article 115 of the Labor Code 2019"
        ),
        rule_condition=(
            '{"field": "leave_type", "operator": "equals", "value": "wedding"}'
        ),
        rule_action=(
            '{"type": "calculate", "parameters": {"entitlement_days": 3, '
            '"leave_type": "wedding"}}'
        ),
        priority=240,
        legal_constraints=(
            '{"min_value": 3, "description": "Article 115 Labor Code 2019 - '
            'minimum 3 days wedding leave"}'
        ),
    )))

    conn.execute(text(_insert_template(
        domain="leave",
        rule_id="leave-funeral-entitlement",
        name="Funeral Leave Entitlement",
        description=(
            "Funeral leave of 3 days per Article 115 of the Labor Code 2019"
        ),
        rule_condition=(
            '{"field": "leave_type", "operator": "equals", "value": "funeral"}'
        ),
        rule_action=(
            '{"type": "calculate", "parameters": {"entitlement_days": 3, '
            '"leave_type": "funeral"}}'
        ),
        priority=250,
        legal_constraints=(
            '{"min_value": 3, "description": "Article 115 Labor Code 2019 - '
            'minimum 3 days funeral leave"}'
        ),
    )))

    conn.execute(text(_insert_template(
        domain="leave",
        rule_id="leave-approval-requirement",
        name="Leave Approval Requirement",
        description=(
            "All leave requests require approval by the employee direct "
            "manager as defined in the organizational hierarchy"
        ),
        rule_condition=(
            '{"field": "requires_approval", "operator": "equals", "value": true}'
        ),
        rule_action=(
            '{"type": "restrict", "parameters": {"approval_required": true, '
            '"approver": "direct_manager"}}'
        ),
        priority=260,
    )))

    # =========================================================================
    # OVERTIME TEMPLATES (Requirement 2.6)
    # =========================================================================

    conn.execute(text(_insert_template(
        domain="overtime",
        rule_id="overtime-max-daily-total",
        name="Maximum Daily Total Hours",
        description=(
            "Total working hours (regular + overtime) must not exceed 12 hours "
            "per day per Article 107 of the Labor Code 2019"
        ),
        rule_condition=(
            '{"field": "total_daily_hours", "operator": "greater_than", "value": 12}'
        ),
        rule_action=(
            '{"type": "restrict", "parameters": {"max_total_daily_hours": 12, '
            '"message": "Total daily hours cannot exceed 12"}}'
        ),
        priority=300,
        legal_constraints=(
            '{"min_value": 12, "description": "Article 107 Labor Code 2019 - '
            'max 12 hours total per day"}'
        ),
    )))

    conn.execute(text(_insert_template(
        domain="overtime",
        rule_id="overtime-max-monthly",
        name="Maximum Monthly Overtime",
        description=(
            "Maximum overtime hours per month is 40 hours per Article 107 "
            "of the Labor Code 2019"
        ),
        rule_condition=(
            '{"field": "monthly_overtime_hours", "operator": "greater_than", '
            '"value": 40}'
        ),
        rule_action=(
            '{"type": "restrict", "parameters": {"max_monthly_hours": 40, '
            '"message": "Monthly overtime cannot exceed 40 hours"}}'
        ),
        priority=310,
        legal_constraints=(
            '{"min_value": 40, "description": "Article 107 Labor Code 2019 - '
            'max 40 hours overtime per month"}'
        ),
    )))

    conn.execute(text(_insert_template(
        domain="overtime",
        rule_id="overtime-max-yearly",
        name="Maximum Yearly Overtime",
        description=(
            "Maximum overtime hours per year is 200 hours (default), "
            "configurable up to 300 hours for special sectors per Article 107"
        ),
        rule_condition=(
            '{"field": "yearly_overtime_hours", "operator": "greater_than", '
            '"value": 200}'
        ),
        rule_action=(
            '{"type": "restrict", "parameters": {"max_yearly_hours": 200, '
            '"max_special_sector": 300, '
            '"message": "Yearly overtime cannot exceed configured maximum"}}'
        ),
        priority=320,
        legal_constraints=(
            '{"min_value": 200, "max_value": 300, '
            '"description": "Article 107 Labor Code 2019 - '
            'max 200h default, 300h for special sectors"}'
        ),
    )))

    conn.execute(text(_insert_template(
        domain="overtime",
        rule_id="overtime-weekday-multiplier",
        name="Weekday Overtime Multiplier",
        description=(
            "Overtime pay multiplier of at least 150%% for normal working days "
            "per Article 98 of the Labor Code 2019"
        ),
        rule_condition=(
            '{"field": "day_type", "operator": "equals", "value": "weekday"}'
        ),
        rule_action=(
            '{"type": "calculate", "parameters": {"multiplier": 150, '
            '"unit": "percent", "day_type": "weekday"}}'
        ),
        priority=330,
        legal_constraints=(
            '{"min_value": 150, "min_values": {"multiplier": 150}, '
            '"description": "Article 98 Labor Code 2019 - '
            'minimum 150%% for weekday overtime"}'
        ),
    )))

    conn.execute(text(_insert_template(
        domain="overtime",
        rule_id="overtime-weekend-multiplier",
        name="Weekend Overtime Multiplier",
        description=(
            "Overtime pay multiplier of at least 200%% for rest days "
            "per Article 98 of the Labor Code 2019"
        ),
        rule_condition=(
            '{"field": "day_type", "operator": "equals", "value": "weekend"}'
        ),
        rule_action=(
            '{"type": "calculate", "parameters": {"multiplier": 200, '
            '"unit": "percent", "day_type": "weekend"}}'
        ),
        priority=340,
        legal_constraints=(
            '{"min_value": 200, "min_values": {"multiplier": 200}, '
            '"description": "Article 98 Labor Code 2019 - '
            'minimum 200%% for weekend overtime"}'
        ),
    )))

    conn.execute(text(_insert_template(
        domain="overtime",
        rule_id="overtime-holiday-multiplier",
        name="Holiday Overtime Multiplier",
        description=(
            "Overtime pay multiplier of at least 300%% for public holidays "
            "per Article 98 of the Labor Code 2019"
        ),
        rule_condition=(
            '{"field": "day_type", "operator": "equals", "value": "holiday"}'
        ),
        rule_action=(
            '{"type": "calculate", "parameters": {"multiplier": 300, '
            '"unit": "percent", "day_type": "holiday"}}'
        ),
        priority=350,
        legal_constraints=(
            '{"min_value": 300, "min_values": {"multiplier": 300}, '
            '"description": "Article 98 Labor Code 2019 - '
            'minimum 300%% for holiday overtime"}'
        ),
    )))

    # =========================================================================
    # DISCIPLINARY TEMPLATES (Requirements 2.7, 2.8, 2.9)
    # =========================================================================

    # --- Four Discipline Forms with Escalation (Requirement 2.7) ---

    conn.execute(text(_insert_template(
        domain="disciplinary",
        rule_id="disciplinary-form-reprimand",
        name="Reprimand (Khiển trách)",
        description=(
            "First level of discipline per Article 124: verbal or written "
            "reprimand for minor violations"
        ),
        rule_condition=(
            '{"field": "violation_severity", "operator": "equals", "value": "minor"}'
        ),
        rule_action=(
            '{"type": "escalate", "parameters": {"form": "reprimand", '
            '"form_vi": "khien_trach", "escalation_level": 1, '
            '"next_form": "salary_increase_extension"}}'
        ),
        priority=400,
    )))

    conn.execute(text(_insert_template(
        domain="disciplinary",
        rule_id="disciplinary-form-salary-extension",
        name="Extension of Salary Increase Period (Kéo dài thời hạn nâng lương)",
        description=(
            "Second level of discipline per Article 124: extension of salary "
            "increase period for up to 6 months"
        ),
        rule_condition=(
            '{"field": "violation_severity", "operator": "equals", '
            '"value": "moderate"}'
        ),
        rule_action=(
            '{"type": "escalate", "parameters": {"form": "salary_increase_extension", '
            '"form_vi": "keo_dai_thoi_han_nang_luong", "escalation_level": 2, '
            '"max_extension_months": 6, "next_form": "demotion"}}'
        ),
        priority=410,
    )))

    conn.execute(text(_insert_template(
        domain="disciplinary",
        rule_id="disciplinary-form-demotion",
        name="Demotion (Cách chức)",
        description=(
            "Third level of discipline per Article 124: demotion from "
            "current position"
        ),
        rule_condition=(
            '{"field": "violation_severity", "operator": "equals", "value": "serious"}'
        ),
        rule_action=(
            '{"type": "escalate", "parameters": {"form": "demotion", '
            '"form_vi": "cach_chuc", "escalation_level": 3, '
            '"next_form": "dismissal"}}'
        ),
        priority=420,
    )))

    conn.execute(text(_insert_template(
        domain="disciplinary",
        rule_id="disciplinary-form-dismissal",
        name="Dismissal (Sa thải)",
        description=(
            "Fourth and highest level of discipline per Article 124: "
            "termination of employment"
        ),
        rule_condition=(
            '{"field": "violation_severity", "operator": "equals", '
            '"value": "very_serious"}'
        ),
        rule_action=(
            '{"type": "escalate", "parameters": {"form": "dismissal", '
            '"form_vi": "sa_thai", "escalation_level": 4, '
            '"is_terminal": true}}'
        ),
        priority=430,
    )))

    # --- Dismissal Triggers (Requirement 2.8) ---

    conn.execute(text(_insert_template(
        domain="disciplinary",
        rule_id="disciplinary-dismissal-5-in-30",
        name="Dismissal Trigger: 5 Unauthorized Absences in 30 Days",
        description=(
            "Automatic dismissal eligibility per Article 125: 5 cumulative "
            "unauthorized absence days within a rolling 30-day window"
        ),
        rule_condition=(
            '{"field": "unauthorized_absences_30d", "operator": "greater_than_or_equal", '
            '"value": 5}'
        ),
        rule_action=(
            '{"type": "escalate", "parameters": {"trigger": "dismissal_eligible", '
            '"reason": "5_absences_in_30_days", "window_days": 30, '
            '"threshold": 5, "article": "125"}}'
        ),
        priority=440,
    )))

    conn.execute(text(_insert_template(
        domain="disciplinary",
        rule_id="disciplinary-dismissal-20-in-365",
        name="Dismissal Trigger: 20 Unauthorized Absences in 365 Days",
        description=(
            "Automatic dismissal eligibility per Article 125: 20 cumulative "
            "unauthorized absence days within a rolling 365-day window"
        ),
        rule_condition=(
            '{"field": "unauthorized_absences_365d", "operator": "greater_than_or_equal", '
            '"value": 20}'
        ),
        rule_action=(
            '{"type": "escalate", "parameters": {"trigger": "dismissal_eligible", '
            '"reason": "20_absences_in_365_days", "window_days": 365, '
            '"threshold": 20, "article": "125"}}'
        ),
        priority=450,
    )))

    # --- Statute of Limitations (Requirement 2.9) ---

    conn.execute(text(_insert_template(
        domain="disciplinary",
        rule_id="disciplinary-statute-general",
        name="Statute of Limitations: General (6 Months)",
        description=(
            "Disciplinary action must be initiated within 6 months from "
            "the date of violation for general violations"
        ),
        rule_condition=(
            '{"field": "days_since_violation", "operator": "greater_than", '
            '"value": 180}'
        ),
        rule_action=(
            '{"type": "restrict", "parameters": {"blocked": true, '
            '"reason": "statute_of_limitations_expired", '
            '"limit_months": 6, "category": "general"}}'
        ),
        priority=460,
    )))

    conn.execute(text(_insert_template(
        domain="disciplinary",
        rule_id="disciplinary-statute-finance",
        name="Statute of Limitations: Finance/Asset (12 Months)",
        description=(
            "Disciplinary action must be initiated within 12 months from "
            "the date of violation for finance or asset-related violations"
        ),
        rule_condition=(
            '{"field": "days_since_violation", "operator": "greater_than", '
            '"value": 365}'
        ),
        rule_action=(
            '{"type": "restrict", "parameters": {"blocked": true, '
            '"reason": "statute_of_limitations_expired", '
            '"limit_months": 12, "category": "finance_asset"}}'
        ),
        priority=470,
    )))


def downgrade() -> None:
    """Remove all seeded policy templates."""
    conn = op.get_bind()
    conn.execute(text("DELETE FROM policy_templates"))
