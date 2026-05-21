"""Seed script: Create leave balances for all employees and sample leave requests.

- Creates leave_balances for all active employees for 2026
- Creates ~15 sample leave_requests with mixed statuses

Usage:
    cd backend
    python -m scripts.seed_leave
"""

from __future__ import annotations

import asyncio
import random
import sys
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

# Add backend/src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

YEAR = 2026

# Leave type defaults (matching migration seed data)
LEAVE_TYPE_DEFAULTS = {
    "annual": 12,
    "sick": 30,
    "unpaid": 0,
    "maternity": 180,
    "wedding": 3,
    "funeral": 3,
    "personal": 5,
}

# Sample reasons for leave requests
REASONS = [
    "Về quê thăm gia đình",
    "Khám sức khỏe định kỳ",
    "Đám cưới bạn thân",
    "Nghỉ ốm (cảm cúm)",
    "Việc cá nhân",
    "Du lịch gia đình",
    "Chăm con ốm",
    "Đi công chứng giấy tờ",
    "Nghỉ phép năm",
    "Khám bệnh",
    "Đám tang người thân",
    "Nghỉ dưỡng sức",
    "Họp phụ huynh",
    "Sửa nhà",
    "Đi thi bằng lái",
]


async def seed_leave() -> None:
    """Main seed function."""
    from src.modules.identity.infrastructure.config import AuthSettings

    settings = AuthSettings()  # type: ignore[call-arg]
    engine = create_async_engine(settings.database_url, echo=False)
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_maker() as session:
        # Get leave types
        lt_result = await session.execute(text("SELECT id, name FROM leave_types"))
        leave_types = {row[1]: row[0] for row in lt_result.all()}

        if not leave_types:
            print("⚠️  No leave types found. Run migrations first (they seed leave types).")
            return

        print(f"📋 Found {len(leave_types)} leave types: {list(leave_types.keys())}")

        # Get all active employees
        emp_result = await session.execute(
            text("SELECT id FROM employees WHERE is_active = true")
        )
        employee_ids = [row[0] for row in emp_result.all()]

        if not employee_ids:
            print("⚠️  No active employees found. Run employee seed first.")
            return

        print(f"👥 Found {len(employee_ids)} active employees")

        # Clear existing balances and requests for the year
        await session.execute(
            text("DELETE FROM leave_requests WHERE EXTRACT(YEAR FROM start_date) = :year"),
            {"year": YEAR},
        )
        await session.execute(
            text("DELETE FROM leave_balances WHERE year = :year"),
            {"year": YEAR},
        )

        # Create leave balances for all employees
        balance_count = 0
        now = datetime.now(UTC)

        for emp_id in employee_ids:
            for lt_name, lt_id in leave_types.items():
                total_days = LEAVE_TYPE_DEFAULTS.get(lt_name, 5)
                if total_days == 0:
                    # Unpaid leave: no balance needed, set high limit
                    total_days = 365

                await session.execute(
                    text(
                        """
                        INSERT INTO leave_balances
                            (id, employee_id, leave_type_id, year, total_days, used_days, remaining_days, created_at, updated_at)
                        VALUES
                            (:id, :emp_id, :lt_id, :year, :total, :used, :remaining, :now, :now)
                        ON CONFLICT ON CONSTRAINT uq_leave_balance DO NOTHING
                        """
                    ),
                    {
                        "id": uuid4(),
                        "emp_id": emp_id,
                        "lt_id": lt_id,
                        "year": YEAR,
                        "total": total_days,
                        "used": 0,
                        "remaining": total_days,
                        "now": now,
                    },
                )
                balance_count += 1

        print(f"✅ Created {balance_count} leave balances")

        # Create ~15 sample leave requests with mixed statuses
        statuses = ["pending"] * 4 + ["approved"] * 7 + ["rejected"] * 2 + ["cancelled"] * 2
        random.shuffle(statuses)

        # Pick random employees for requests
        request_employees = random.choices(employee_ids, k=15)
        # Use annual and sick leave types mostly
        request_leave_types = (
            [leave_types.get("annual", list(leave_types.values())[0])] * 8
            + [leave_types.get("sick", list(leave_types.values())[0])] * 4
            + [leave_types.get("personal", list(leave_types.values())[0])] * 3
        )
        random.shuffle(request_leave_types)

        request_count = 0
        for i in range(15):
            emp_id = request_employees[i]
            lt_id = request_leave_types[i]
            status = statuses[i]
            reason = REASONS[i]

            # Random start date in 2026
            start_offset = random.randint(0, 300)
            start_date = date(YEAR, 1, 1) + timedelta(days=start_offset)
            # Skip weekends
            while start_date.weekday() >= 5:
                start_date += timedelta(days=1)

            # Duration: 1-5 days
            duration = random.randint(1, 5)
            end_date = start_date + timedelta(days=duration - 1)
            # Skip weekends for end date
            while end_date.weekday() >= 5:
                end_date += timedelta(days=1)

            total_days = duration

            approved_by = None
            approved_at = None
            rejection_reason = None

            if status == "approved":
                approved_at = now
            elif status == "rejected":
                rejection_reason = "Không đủ nhân sự trong thời gian này"

            await session.execute(
                text(
                    """
                    INSERT INTO leave_requests
                        (id, employee_id, leave_type_id, start_date, end_date, total_days,
                         reason, status, approved_by, approved_at, rejection_reason,
                         created_at, updated_at)
                    VALUES
                        (:id, :emp_id, :lt_id, :start_date, :end_date, :total_days,
                         :reason, :status, :approved_by, :approved_at, :rejection_reason,
                         :created_at, :updated_at)
                    """
                ),
                {
                    "id": uuid4(),
                    "emp_id": emp_id,
                    "lt_id": lt_id,
                    "start_date": start_date,
                    "end_date": end_date,
                    "total_days": total_days,
                    "reason": reason,
                    "status": status,
                    "approved_by": approved_by,
                    "approved_at": approved_at,
                    "rejection_reason": rejection_reason,
                    "created_at": now - timedelta(days=random.randint(1, 30)),
                    "updated_at": now,
                },
            )
            request_count += 1

        await session.commit()

        print(f"✅ Created {request_count} sample leave requests")
        print(f"   📊 Status distribution:")
        from collections import Counter

        status_dist = Counter(statuses)
        for s, count in status_dist.items():
            print(f"      {s}: {count}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_leave())
