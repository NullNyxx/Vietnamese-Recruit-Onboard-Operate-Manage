"""PII Redactor service for the Recruitment module.

Redacts personally identifiable information from text before sending to LLM.
Handles Vietnamese-specific PII patterns: CCCD/CMND, MST, bank accounts, salary figures.
"""

import re

# Placeholder token for redacted content
REDACTED_TOKEN = "[REDACTED]"


class PIIRedactor:
    """Redacts PII from text before sending to LLM.

    Patterns redacted:
    - CCCD/CMND: 12 consecutive digits (Vietnamese national ID)
    - MST (tax code): 10-13 consecutive digits
    - Bank accounts: 8-19 consecutive digits
    - Salary figures: numbers adjacent to VND/đ/triệu/tr keywords,
      or comma-formatted numbers >= 1,000,000
    """

    def __init__(self) -> None:
        # Salary pattern: numbers followed/preceded by currency keywords
        # Matches: "15 triệu", "15tr", "20,000,000 VND", "15.000.000đ", etc.
        self._salary_keyword_pattern = re.compile(
            r"(?:"
            # Number (with optional comma/dot thousands separators) followed by currency keyword
            r"[\d]+(?:[.,]\d{3})*\s*(?:VND|đồng|đ|triệu|tr)\b"
            r"|"
            # Currency keyword followed by number
            r"(?:VND|đồng|đ|triệu|tr)\s*[\d]+(?:[.,]\d{3})*"
            r")",
            re.IGNORECASE | re.UNICODE,
        )

        # Comma/dot-formatted numbers >= 1,000,000 (e.g., 1,000,000 or 1.000.000)
        # These are likely salary figures in Vietnamese context
        self._large_formatted_number_pattern = re.compile(r"\b\d{1,3}(?:[.,]\d{3}){2,}\b")

        # Consecutive digit patterns (8-19 digits) for CCCD/CMND, MST, bank accounts
        # This single pattern covers:
        # - CCCD/CMND: 12 digits
        # - MST: 10-13 digits
        # - Bank accounts: 8-19 digits
        self._consecutive_digits_pattern = re.compile(r"\b\d{8,19}\b")

    def redact(self, text: str) -> str:
        """Replace PII patterns with [REDACTED] placeholder.

        Handles overlapping patterns by processing salary keywords first
        (more specific), then large formatted numbers, then consecutive digits.
        Uses a span-tracking approach to avoid double-redaction.

        Args:
            text: Input text potentially containing PII.

        Returns:
            Text with PII replaced by [REDACTED] tokens.
        """
        if not text:
            return text

        # Collect all spans to redact, then apply them in one pass
        # to handle overlapping patterns gracefully
        spans_to_redact: list[tuple[int, int]] = []

        # 1. Salary keyword patterns (most specific - numbers with currency keywords)
        for match in self._salary_keyword_pattern.finditer(text):
            spans_to_redact.append((match.start(), match.end()))

        # 2. Large comma/dot-formatted numbers >= 1,000,000
        for match in self._large_formatted_number_pattern.finditer(text):
            # Verify the numeric value is >= 1,000,000
            num_str = match.group().replace(",", "").replace(".", "")
            try:
                if int(num_str) >= 1_000_000:
                    spans_to_redact.append((match.start(), match.end()))
            except ValueError:
                continue

        # 3. Consecutive digits (8-19 digits) for CCCD, MST, bank accounts
        for match in self._consecutive_digits_pattern.finditer(text):
            spans_to_redact.append((match.start(), match.end()))

        if not spans_to_redact:
            return text

        # Merge overlapping spans to avoid double-redaction
        merged_spans = self._merge_spans(spans_to_redact)

        # Build result by replacing spans from end to start
        # (to preserve character positions)
        result = text
        for start, end in reversed(merged_spans):
            result = result[:start] + REDACTED_TOKEN + result[end:]

        return result

    @staticmethod
    def _merge_spans(spans: list[tuple[int, int]]) -> list[tuple[int, int]]:
        """Merge overlapping or adjacent spans into non-overlapping spans.

        Args:
            spans: List of (start, end) tuples.

        Returns:
            Sorted list of merged (start, end) tuples.
        """
        if not spans:
            return []

        # Sort by start position, then by end position (descending) for ties
        sorted_spans = sorted(spans, key=lambda s: (s[0], -s[1]))

        merged: list[tuple[int, int]] = [sorted_spans[0]]
        for start, end in sorted_spans[1:]:
            last_start, last_end = merged[-1]
            if start <= last_end:
                # Overlapping or adjacent — extend the last span
                merged[-1] = (last_start, max(last_end, end))
            else:
                merged.append((start, end))

        return merged
