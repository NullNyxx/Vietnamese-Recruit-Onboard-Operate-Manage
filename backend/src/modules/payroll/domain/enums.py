from enum import StrEnum


class PayrollStatus(StrEnum):
    DRAFT = "draft"
    CALCULATING = "calculating"
    CONFIRMED = "confirmed"
    PAID = "paid"


class AllowanceType(StrEnum):
    TELEPHONE = "telephone"
    TRANSPORT = "transport"
    MEAL = "meal"
    HOUSING = "housing"
    RESPONSIBILITY = "responsibility"
    OTHER = "other"


class ContractType(StrEnum):
    OFFICIAL = "official"
    PROBATION = "probation"
    CONTRACTOR = "contractor"