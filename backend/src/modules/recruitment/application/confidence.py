"""Confidence score calculator for parsed CV data.

Calculates a confidence score between 0.0 and 1.0 based on the
presence and completeness of fields extracted from a CV by the LLM.
"""

from src.modules.recruitment.domain.value_objects import ParsedCV


def calculate_confidence_score(parsed_cv: ParsedCV) -> float:
    """Calculate confidence score for a parsed CV.

    The score is a weighted sum of field presence checks:
      - name present and non-empty: 0.25
      - email present and non-empty: 0.25
      - phone present and non-empty: 0.10
      - skills list has at least 1 item: 0.10
      - experience list has at least 1 item: 0.15
      - education list has at least 1 item: 0.10
      - summary present and non-empty: 0.05

    Args:
        parsed_cv: A ParsedCV value object with extracted CV fields.

    Returns:
        A float in the range [0.0, 1.0] representing extraction confidence.
    """
    score = 0.0

    if parsed_cv.name and parsed_cv.name.strip():
        score += 0.25

    if parsed_cv.email and parsed_cv.email.strip():
        score += 0.25

    if parsed_cv.phone and parsed_cv.phone.strip():
        score += 0.10

    if parsed_cv.skills and len(parsed_cv.skills) >= 1:
        score += 0.10

    if parsed_cv.experience and len(parsed_cv.experience) >= 1:
        score += 0.15

    if parsed_cv.education and len(parsed_cv.education) >= 1:
        score += 0.10

    if parsed_cv.summary and parsed_cv.summary.strip():
        score += 0.05

    # Clamp to [0.0, 1.0] to guard against floating point drift
    return max(0.0, min(1.0, score))
