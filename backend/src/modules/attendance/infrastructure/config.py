"""Configuration for the Attendance module."""

from pydantic_settings import BaseSettings


class AttendanceSettings(BaseSettings):
    """Settings for attendance and leave management."""

    # Leave settings
    max_carry_over_days: int = 5  # Max annual leave days carried to next year
    annual_leave_base_days: int = 12  # Base annual leave (Vietnamese labor law)
    seniority_bonus_years: int = 5  # Every N years → +1 day

    # Attendance settings
    default_start_time: str = "08:00"
    default_end_time: str = "17:00"
    default_break_minutes: int = 60
    late_threshold_minutes: int = 15
    early_leave_threshold_minutes: int = 15

    # Overtime settings
    max_ot_per_day_hours: float = 4.0
    max_ot_per_week_hours: float = 20.0
    ot_rate_weekday: float = 1.5
    ot_rate_weekend: float = 2.0
    ot_rate_holiday: float = 3.0

    model_config = {"env_prefix": "ATTENDANCE_"}
