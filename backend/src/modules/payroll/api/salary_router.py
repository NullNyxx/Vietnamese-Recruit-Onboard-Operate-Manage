from typing import Sequence
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from src.database import get_session
from src.modules.payroll.application.salary_service import SalaryService
from src.modules.payroll.api import schemas

router = APIRouter(prefix="/api/payroll/salary", tags=["Salary Config"])


def get_salary_service(session: Session = Depends(get_session)) -> SalaryService:
    return SalaryService(session)


@router.post("/config", response_model=schemas.SalaryConfigResponse)
def create_salary_config(
    data: schemas.SalaryConfigCreate,
    service: SalaryService = Depends(get_salary_service),
):
    try:
        config = service.create_salary_config(
            employee_id=data.employee_id,
            gross_salary=data.gross_salary,
            insurance_salary=data.insurance_salary,
            contract_type=data.contract_type,
            effective_date=data.effective_date,
        )
        return config
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/config/{employee_id}", response_model=schemas.SalaryConfigResponse)
def get_salary_config(
    employee_id: UUID,
    service: SalaryService = Depends(get_salary_service),
):
    config = service.get_salary_config(employee_id)
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Salary config not found")
    return config


@router.put("/config/{employee_id}", response_model=schemas.SalaryConfigResponse)
def update_salary_config(
    employee_id: UUID,
    data: schemas.SalaryConfigUpdate,
    service: SalaryService = Depends(get_salary_service),
):
    try:
        config = service.update_salary_config(
            employee_id=employee_id,
            gross_salary=data.gross_salary,
            insurance_salary=data.insurance_salary,
            contract_type=data.contract_type,
            effective_date=data.effective_date,
        )
        return config
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/config/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_salary_config(
    employee_id: UUID,
    service: SalaryService = Depends(get_salary_service),
):
    try:
        service.delete_salary_config(employee_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/allowances", response_model=schemas.AllowanceResponse)
def create_allowance(
    data: schemas.AllowanceCreate,
    service: SalaryService = Depends(get_salary_service),
):
    try:
        allowance = service.create_allowance(
            employee_id=data.employee_id,
            allowance_type=data.allowance_type,
            amount=data.amount,
            is_taxable=data.is_taxable,
            effective_date=data.effective_date,
            end_date=data.end_date,
        )
        return allowance
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/allowances/{employee_id}", response_model=list[schemas.AllowanceResponse])
def get_allowances(
    employee_id: UUID,
    service: SalaryService = Depends(get_salary_service),
):
    allowances = service.get_allowances(employee_id)
    return allowances


@router.put("/allowances/{allowance_id}", response_model=schemas.AllowanceResponse)
def update_allowance(
    allowance_id: UUID,
    data: schemas.AllowanceUpdate,
    service: SalaryService = Depends(get_salary_service),
):
    try:
        allowance = service.update_allowance(
            allowance_id=allowance_id,
            amount=data.amount,
            is_taxable=data.is_taxable,
            end_date=data.end_date,
        )
        return allowance
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/allowances/{allowance_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_allowance(
    allowance_id: UUID,
    service: SalaryService = Depends(get_salary_service),
):
    try:
        service.delete_allowance(allowance_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/dependents", response_model=schemas.DependentResponse)
def create_dependent(
    data: schemas.DependentCreate,
    service: SalaryService = Depends(get_salary_service),
):
    try:
        dependent = service.create_dependent(
            employee_id=data.employee_id,
            name=data.name,
            relationship=data.relationship,
            date_of_birth=data.date_of_birth,
            tax_dependent=data.tax_dependent,
        )
        return dependent
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/dependents/{employee_id}", response_model=list[schemas.DependentResponse])
def get_dependents(
    employee_id: UUID,
    service: SalaryService = Depends(get_salary_service),
):
    dependents = service.get_dependents(employee_id)
    return dependents


@router.put("/dependents/{dependent_id}", response_model=schemas.DependentResponse)
def update_dependent(
    dependent_id: UUID,
    data: schemas.DependentUpdate,
    service: SalaryService = Depends(get_salary_service),
):
    try:
        dependent = service.update_dependent(
            dependent_id=dependent_id,
            name=data.name,
            relationship=data.relationship,
            date_of_birth=data.date_of_birth,
            tax_dependent=data.tax_dependent,
        )
        return dependent
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/dependents/{dependent_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dependent(
    dependent_id: UUID,
    service: SalaryService = Depends(get_salary_service),
):
    try:
        service.delete_dependent(dependent_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/position-salaries", response_model=schemas.PositionSalaryResponse)
def create_position_salary(
    data: schemas.PositionSalaryCreate,
    session: Session = Depends(get_session),
):
    from src.modules.payroll.domain.entities import PositionSalary

    ps = PositionSalary(
        position_id=data.position_id,
        grade=data.grade,
        min_salary=data.min_salary,
        mid_salary=data.mid_salary,
        max_salary=data.max_salary,
        effective_date=data.effective_date,
    )
    session.add(ps)
    session.commit()
    session.refresh(ps)
    return ps


@router.get("/position-salaries/{position_id}", response_model=list[schemas.PositionSalaryResponse])
def get_position_salaries(
    position_id: UUID,
    session: Session = Depends(get_session),
):
    from src.modules.payroll.domain.entities import PositionSalary
    from sqlmodel import select

    salaries = session.exec(
        select(PositionSalary)
        .where(PositionSalary.position_id == position_id)
        .order_by(PositionSalary.grade)
    ).all()
    return salaries


@router.get("/positions/salary-suggestions", response_model=list[schemas.PositionSalarySuggestion])
def get_salary_suggestions(
    session: Session = Depends(get_session),
):
    from src.modules.payroll.domain.entities import PositionSalary
    from src.modules.employee.domain.entities import Position
    from sqlmodel import select

    positions = session.exec(select(Position)).all()
    result = []

    for pos in positions:
        salaries = session.exec(
            select(PositionSalary)
            .where(PositionSalary.position_id == pos.id)
            .order_by(PositionSalary.grade)
        ).all()
        if salaries:
            result.append(
                schemas.PositionSalarySuggestion(
                    position_id=pos.id,
                    position_name=pos.name,
                    grades=[schemas.PositionSalaryResponse.model_validate(s) for s in salaries],
                )
            )

    return result
