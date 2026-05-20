"""Domain value objects for the Recruitment CV Pipeline module.

Defines Pydantic BaseModel classes representing structured data
extracted from CVs. These are immutable value objects used throughout
the application layer for data transfer and validation.
"""

from pydantic import BaseModel, Field


class ExperienceItem(BaseModel):
    """A single work experience entry extracted from a CV.

    Represents one position held by the candidate, including
    company name, job title, duration, and description.
    """

    company: str = Field(max_length=200)
    title: str = Field(max_length=200)
    duration: str = Field(default="", max_length=100)
    description: str = Field(default="", max_length=1000)


class EducationItem(BaseModel):
    """A single education entry extracted from a CV.

    Represents one educational qualification including institution,
    degree type, field of study, and graduation year.
    """

    institution: str = Field(max_length=200)
    degree: str = Field(default="", max_length=100)
    field: str = Field(default="", max_length=200)
    year: str = Field(default="", max_length=20)


class ParsedCV(BaseModel):
    """Structured data extracted from a CV via LLM parsing.

    Contains the key fields that the LLM extracts from OCR text,
    used to create or update Candidate records. Fields have maximum
    lengths to prevent storage issues and ensure data quality.
    """

    name: str = Field(max_length=200)
    email: str = Field(max_length=254)
    phone: str = Field(default="", max_length=20)
    skills: list[str] = Field(default_factory=list, max_length=50)
    experience: list[ExperienceItem] = Field(default_factory=list, max_length=20)
    education: list[EducationItem] = Field(default_factory=list, max_length=10)
    summary: str = Field(default="", max_length=500)
