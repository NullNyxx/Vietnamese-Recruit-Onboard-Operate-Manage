"""Unit tests for the confidence score calculator."""

from src.modules.recruitment.application.confidence import calculate_confidence_score
from src.modules.recruitment.domain.value_objects import (
    EducationItem,
    ExperienceItem,
    ParsedCV,
)


class TestCalculateConfidenceScore:
    """Tests for calculate_confidence_score function."""

    def test_all_fields_present_returns_1_0(self):
        """A fully populated CV gets a perfect score of 1.0."""
        cv = ParsedCV(
            name="Nguyen Van A",
            email="a@example.com",
            phone="0901234567",
            skills=["Python"],
            experience=[ExperienceItem(company="Acme", title="Dev")],
            education=[EducationItem(institution="HUST")],
            summary="Experienced developer",
        )
        assert calculate_confidence_score(cv) == 1.0

    def test_empty_cv_returns_0_0(self):
        """A CV with all empty/default fields gets 0.0."""
        cv = ParsedCV(
            name="",
            email="",
            phone="",
            skills=[],
            experience=[],
            education=[],
            summary="",
        )
        assert calculate_confidence_score(cv) == 0.0

    def test_only_name_and_email_returns_0_5(self):
        """Name + email contribute 0.25 + 0.25 = 0.5."""
        cv = ParsedCV(
            name="Nguyen Van A",
            email="a@example.com",
            phone="",
            skills=[],
            experience=[],
            education=[],
            summary="",
        )
        assert calculate_confidence_score(cv) == 0.5

    def test_whitespace_only_fields_not_counted(self):
        """Fields containing only whitespace are treated as empty."""
        cv = ParsedCV(
            name="   ",
            email="  ",
            phone=" ",
            skills=[],
            experience=[],
            education=[],
            summary="   ",
        )
        assert calculate_confidence_score(cv) == 0.0

    def test_phone_adds_0_1(self):
        """Phone field contributes 0.10."""
        cv = ParsedCV(
            name="",
            email="",
            phone="0901234567",
            skills=[],
            experience=[],
            education=[],
            summary="",
        )
        assert calculate_confidence_score(cv) == 0.10

    def test_skills_adds_0_1(self):
        """Skills list with at least one item contributes 0.10."""
        cv = ParsedCV(
            name="",
            email="",
            phone="",
            skills=["Python"],
            experience=[],
            education=[],
            summary="",
        )
        assert calculate_confidence_score(cv) == 0.10

    def test_experience_adds_0_15(self):
        """Experience list with at least one item contributes 0.15."""
        cv = ParsedCV(
            name="",
            email="",
            phone="",
            skills=[],
            experience=[ExperienceItem(company="Acme", title="Dev")],
            education=[],
            summary="",
        )
        assert calculate_confidence_score(cv) == 0.15

    def test_education_adds_0_1(self):
        """Education list with at least one item contributes 0.10."""
        cv = ParsedCV(
            name="",
            email="",
            phone="",
            skills=[],
            experience=[],
            education=[EducationItem(institution="HUST")],
            summary="",
        )
        assert calculate_confidence_score(cv) == 0.10

    def test_summary_adds_0_05(self):
        """Summary field contributes 0.05."""
        cv = ParsedCV(
            name="",
            email="",
            phone="",
            skills=[],
            experience=[],
            education=[],
            summary="A brief summary",
        )
        assert calculate_confidence_score(cv) == 0.05

    def test_result_always_bounded_0_to_1(self):
        """Result is always in [0.0, 1.0] range."""
        cv = ParsedCV(
            name="Nguyen Van A",
            email="a@example.com",
            phone="0901234567",
            skills=["Python", "Java", "Go"],
            experience=[
                ExperienceItem(company="A", title="Dev"),
                ExperienceItem(company="B", title="Lead"),
            ],
            education=[
                EducationItem(institution="HUST"),
                EducationItem(institution="MIT"),
            ],
            summary="Senior developer with 10 years experience",
        )
        score = calculate_confidence_score(cv)
        assert 0.0 <= score <= 1.0

    def test_deterministic_same_input_same_output(self):
        """Same input always produces the same output."""
        cv = ParsedCV(
            name="Nguyen Van A",
            email="a@example.com",
            phone="0901234567",
            skills=["Python"],
            experience=[ExperienceItem(company="Acme", title="Dev")],
            education=[EducationItem(institution="HUST")],
            summary="Summary",
        )
        scores = [calculate_confidence_score(cv) for _ in range(100)]
        assert all(s == scores[0] for s in scores)

    def test_threshold_scenario_exactly_0_7(self):
        """Name + email + experience + education = 0.25+0.25+0.15+0.10 = 0.75 (above threshold)."""
        cv = ParsedCV(
            name="Nguyen Van A",
            email="a@example.com",
            phone="",
            skills=[],
            experience=[ExperienceItem(company="Acme", title="Dev")],
            education=[EducationItem(institution="HUST")],
            summary="",
        )
        score = calculate_confidence_score(cv)
        assert score == 0.75
        assert score >= 0.7
