"""Seed script: Generate 1 month of random attendance data for all active employees.

Distribution: 70% present, 20% late, 5% absent, 5% early_leave.
Skips weekends and holidays.

Usage:
    cd backend
    python -m scripts.seed_attendance
"""

from __future__ import annotations

import asyncio
import random
import sys
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from uuid import uuid4

# Add backend/src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Settings
YEAR = 2026
MONTH = 5
SCHEDULE_START = time(8, 0)
SCHEDULE_END = time(17, 0)
BREAK_MINUTES = 60


def random_checkin_time(status: str, work_date: date) -> datetime:
    """Generate a random check-in time based on status."""
    base = datetime.combine(work_date, SCHEDULE_START, tzinfo=UTC)

    if status == "present":
        # On time: -10 to +10 minutes
        offset = random.randint(-10, 10)
    elif status == "late":
        # Late: 16 to 60 minutes after start
        offset = random.randint(16, 60)
    elif status == "early_leave":
        # Normal check-in
        offset = random.randint(-5, 5)
    else:
        return base

    return base + timedelta(minutes=offset)


def random_checkout_time(status: str, work_date: date) -> datetime:
    """Generate a random check-out time based on status."""
    base = datetime.combine(work_date, SCHEDULE_END, tzinfo=UTC)

    if status == "present":
        # Normal: 0 to +30 minutes after end
        offset = random.randint(0, 30)
    elif status == "late":
        # Normal checkout
        offset = random.randint(0, 15)
    elif status == "early_leave":
        # Leave 30-90 minutes early
        offset = random.randint(-90, -30)
    else:
        return base

    return base + timedelta(minutes=offset)


def calculate_work_hours(check_in: datetime, check_out: datetime) -> float:
    """Calculate work hours minus break."""
    diff = (check_out - check_in).total_seconds() / 3600
    work = max(0, diff - (BREAK_MINUTES / 60))
    return round(work, 2)


async def seed_attendance() -> None:
    """Main seed function."""
    from src.modules.identity.infrastructure.config import AuthSettings

    settings = AuthSettings()  # type: ignore[call-arg]
    engine = create_async_engine(settings.database_url, echo=False)
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_maker() as session:
        # Get all active employees
        result = await session.execute(
            text("SELECT id FROM employees WHERE is_active = true")
        )
        employee_ids = [row[0] for row in result.all()]

        if not employee_ids:
            print("⚠️  No active employees found. Run employee seed first.")
            return

        print(f"📋 Found {len(employee_ids)} active employees")

        # Get holidays for the month
        import calendar

        _, last_day = calendar.monthrange(YEAR, MONTH)
        start_date = date(YEAR, MONTH, 1)
        end_date = date(YEAR, MONTH, last_day)

        holiday_result = await session.execute(
            text(
                "SELECT holiday_date FROM holidays WHERE holiday_date >= :start AND holiday_date <= :end"
            ),
            {"start": start_date, "end": end_date},
        )
        holidays = {row[0] for row in holiday_result.all()}

        # Clear existing attendance for this month
        await session.execute(
            text(
                "DELETE FROM attendance_records WHERE work_date >= :start AND work_date <= :end"
            ),
            {"start": start_date, "end": end_date},
        )

        # Generate records
        total_records = 0
        status_counts = {"present": 0, "late": 0, "absent": 0, "early_leave": 0}

        for emp_id in employee_ids:
            for day in range(1, last_day + 1):
                current_date = date(YEAR, MONTH, day)

                # Skip weekends
                if current_date.weekday() >= 5:
                    continue

                # Skip holidays
                if current_date in holidays:
                    continue

                # Determine status based on distribution
                rand = random.random()
                if rand < 0.70:
                    status = "present"
                elif rand < 0.90:
                    status = "late"
                elif rand < 0.95:
                    status = "absent"
                else:
                    status = "early_leave"

                status_counts[status] += 1
                now = datetime.now(UTC)

                if status == "absent":
                    # No check-in/out for absent
                    await session.execute(
                        text(
                            """
                            INSERT INTO attendance_records
                                (id, employee_id, work_date, status, created_at, updated_at)
                            VALUES
                                (:id, :emp_id, :work_date, :status, :now, :now)
                            """
                        ),
                        {
                            "id": uuid4(),
                            "emp_id": emp_id,
                            "work_date": current_date,
                            "status": status,
                            "now": now,
                        },
                    )
                else:
                    check_in = random_checkin_time(status, current_date)
                    check_out = random_checkout_time(status, current_date)
                    work_hours = calculate_work_hours(check_in, check_out)
                    overtime = max(0, round(work_hours - 8.0, 2)) if status == "present" else 0

                    await session.execute(
                        text(
                            """
                            INSERT INTO attendance_records
                                (id, employee_id, work_date, check_in, check_out,
                                 work_hours, overtime_hours, status, created_at, updated_at)
                            VALUES
                                (:id, :emp_id, :work_date, :check_in, :check_out,
                                 :work_hours, :overtime, :status, :now, :now)
                            """
                        ),
                        {
                            "id": uuid4(),
                            "emp_id": emp_id,
                            "work_date": current_date,
                            "check_in": check_in,
                            "check_out": check_out,
                            "work_hours": work_hours,
                            "overtime": overtime,
                            "status": status,
                            "now": now,
                        },
                    )

                total_records += 1

        await session.commit()

        print(f"✅ Seeded {total_records} attendance records for {MONTH}/{YEAR}")
        print(f"   📊 Distribution:")
        print(f"      Present:     {status_counts['present']}")
        print(f"      Late:        {status_counts['late']}")
        print(f"      Absent:      {status_counts['absent']}")
        print(f"      Early leave: {status_counts['early_leave']}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_attendance())
