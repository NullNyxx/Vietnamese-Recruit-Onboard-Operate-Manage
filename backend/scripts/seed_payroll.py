"""Seed script: Generate salary configs, allowances, and dependents for all active employees.

Usage:
    cd backend
    python -m scripts.seed_payroll
"""

from __future__ import annotations

import asyncio
import random
import sys
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.modules.identity.infrastructure.config import AuthSettings

SALARY_RANGES = {
    "Intern": (Decimal("3000000"), Decimal("5000000")),
    "Junior": (Decimal("7000000"), Decimal("15000000")),
    "Senior": (Decimal("15000000"), Decimal("30000000")),
    "Lead": (Decimal("25000000"), Decimal("45000000")),
    "Manager": (Decimal("35000000"), Decimal("60000000")),
}

ALLOWANCE_TYPES = ["telephone", "transport", "meal", "housing", "responsibility"]

POSITION_ALLOWANCE = {
    "Manager": [("transport", 2000000), ("responsibility", 3000000)],
    "Lead": [("transport", 1500000), ("responsibility", 2000000)],
    "Senior": [("meal", 500000)],
    "Junior": [("meal", 300000)],
    "Intern": [],
}


async def seed_payroll() -> None:
    settings = AuthSettings()
    engine = create_async_engine(settings.database_url, echo=False)
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_maker() as session:
        result = await session.execute(
            text("""
                SELECT e.id, e.employee_code, p.name as position_name
                FROM employees e
                LEFT JOIN positions p ON e.position_id = p.id
                WHERE e.is_active = true
            """)
        )
        employees = result.all()

        if not employees:
            print("⚠️  No active employees found.")
            return

        print(f"📋 Found {len(employees)} active employees")

        config_count = 0
        allowance_count = 0
        dependent_count = 0

        for emp_id, emp_code, position_name in employees:
            position_name = position_name or "Junior"
            level = "Intern"
            for key in SALARY_RANGES:
                if key.lower() in position_name.lower():
                    level = key
                    break

            min_sal, max_sal = SALARY_RANGES.get(level, (Decimal("5000000"), Decimal("15000000")))
            gross = Decimal(random.randint(int(min_sal), int(max_sal)))
            insurance_sal = gross * Decimal("0.9")

            await session.execute(
                text("""
                    INSERT INTO salary_configs
                        (id, employee_id, gross_salary, insurance_salary, contract_type, effective_date, created_at, updated_at)
                    VALUES
                        (:id, :emp_id, :gross, :insurance, 'official', :effective, :now, :now)
                    ON CONFLICT (employee_id) DO NOTHING
                """),
                {
                    "id": uuid4(),
                    "emp_id": emp_id,
                    "gross": gross,
                    "insurance": insurance_sal,
                    "effective": date.today(),
                    "now": text("now()"),
                },
            )
            config_count += 1

            for allow_type, amount in POSITION_ALLOWANCE.get(level, []):
                await session.execute(
                    text("""
                        INSERT INTO allowances
                            (id, employee_id, allowance_type, amount, is_taxable, effective_date, created_at)
                        VALUES
                            (:id, :emp_id, :type, :amount, true, :effective, :now)
                    """),
                    {
                        "id": uuid4(),
                        "emp_id": emp_id,
                        "type": allow_type,
                        "amount": amount,
                        "effective": date.today(),
                        "now": text("now()"),
                    },
                )
                allowance_count += 1

            if random.random() < 0.3:
                num_deps = random.randint(1, 2)
                relationships = ["vợ", "chồng", "con"]
                for i in range(num_deps):
                    await session.execute(
                        text("""
                            INSERT INTO dependents
                                (id, employee_id, name, relationship, date_of_birth, tax_dependent, created_at)
                            VALUES
                                (:id, :emp_id, :name, :rel, :dob, true, :now)
                        """),
                        {
                            "id": uuid4(),
                            "emp_id": emp_id,
                            "name": f"Người thân {i+1}",
                            "rel": random.choice(relationships),
                            "dob": date(1980, 1, 1) + timedelta(days=random.randint(0, 15000)),
                            "now": text("now()"),
                        },
                    )
                    dependent_count += 1

        await session.commit()

        print(f"✅ Seeded payroll data:")
        print(f"   Salary configs: {config_count}")
        print(f"   Allowances: {allowance_count}")
        print(f"   Dependents: {dependent_count}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_payroll())