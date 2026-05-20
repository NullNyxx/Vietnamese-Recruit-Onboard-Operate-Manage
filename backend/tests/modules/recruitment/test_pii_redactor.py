"""Unit tests for the PII Redactor service."""

import pytest

from src.modules.recruitment.infrastructure.pii_redactor import PIIRedactor, REDACTED_TOKEN


@pytest.fixture
def redactor() -> PIIRedactor:
    """Create a PIIRedactor instance for testing."""
    return PIIRedactor()


class TestCCCDRedaction:
    """Tests for CCCD/CMND (12-digit national ID) redaction."""

    def test_redacts_12_digit_cccd(self, redactor: PIIRedactor):
        """A 12-digit number should be redacted as CCCD."""
        text = "Số CCCD: 012345678901"
        result = redactor.redact(text)
        assert REDACTED_TOKEN in result
        assert "012345678901" not in result

    def test_preserves_surrounding_text_for_cccd(self, redactor: PIIRedactor):
        """Text around the CCCD number should remain intact."""
        text = "Số CCCD: 012345678901, cấp ngày 01/01/2020"
        result = redactor.redact(text)
        assert "Số CCCD: " in result
        assert ", cấp ngày 01/01/2020" in result

    def test_redacts_multiple_cccd_numbers(self, redactor: PIIRedactor):
        """Multiple CCCD numbers in the same text should all be redacted."""
        text = "CCCD cũ: 012345678901, CCCD mới: 098765432109"
        result = redactor.redact(text)
        assert "012345678901" not in result
        assert "098765432109" not in result
        assert result.count(REDACTED_TOKEN) == 2


class TestMSTRedaction:
    """Tests for MST (tax code, 10-13 digits) redaction."""

    def test_redacts_10_digit_mst(self, redactor: PIIRedactor):
        """A 10-digit number should be redacted as MST."""
        text = "MST: 0123456789"
        result = redactor.redact(text)
        assert "0123456789" not in result
        assert REDACTED_TOKEN in result

    def test_redacts_13_digit_mst(self, redactor: PIIRedactor):
        """A 13-digit number should be redacted as MST."""
        text = "Mã số thuế: 0123456789012"
        result = redactor.redact(text)
        assert "0123456789012" not in result
        assert REDACTED_TOKEN in result

    def test_preserves_surrounding_text_for_mst(self, redactor: PIIRedactor):
        """Text around the MST should remain intact."""
        text = "Mã số thuế: 0123456789, đăng ký tại TP.HCM"
        result = redactor.redact(text)
        assert "Mã số thuế: " in result
        assert ", đăng ký tại TP.HCM" in result


class TestBankAccountRedaction:
    """Tests for bank account number (8-19 digits) redaction."""

    def test_redacts_8_digit_bank_account(self, redactor: PIIRedactor):
        """An 8-digit number should be redacted as bank account."""
        text = "STK: 12345678"
        result = redactor.redact(text)
        assert "12345678" not in result
        assert REDACTED_TOKEN in result

    def test_redacts_19_digit_bank_account(self, redactor: PIIRedactor):
        """A 19-digit number should be redacted as bank account."""
        text = "Số tài khoản: 1234567890123456789"
        result = redactor.redact(text)
        assert "1234567890123456789" not in result
        assert REDACTED_TOKEN in result

    def test_does_not_redact_7_digit_number(self, redactor: PIIRedactor):
        """A 7-digit number should NOT be redacted (below threshold)."""
        text = "Mã nhân viên: 1234567"
        result = redactor.redact(text)
        assert "1234567" in result

    def test_does_not_redact_20_digit_number(self, redactor: PIIRedactor):
        """A 20-digit number should NOT be redacted (above threshold)."""
        text = "Số dài: 12345678901234567890"
        result = redactor.redact(text)
        assert "12345678901234567890" in result


class TestSalaryRedaction:
    """Tests for salary figure redaction."""

    def test_redacts_number_followed_by_vnd(self, redactor: PIIRedactor):
        """Number followed by VND should be redacted."""
        text = "Lương: 15000000 VND"
        result = redactor.redact(text)
        assert REDACTED_TOKEN in result
        assert "15000000 VND" not in result

    def test_redacts_number_followed_by_dong(self, redactor: PIIRedactor):
        """Number followed by đ should be redacted."""
        text = "Lương cơ bản: 15000000đ"
        result = redactor.redact(text)
        assert REDACTED_TOKEN in result
        assert "15000000đ" not in result

    def test_redacts_number_followed_by_trieu(self, redactor: PIIRedactor):
        """Number followed by triệu should be redacted."""
        text = "Mức lương: 15 triệu"
        result = redactor.redact(text)
        assert REDACTED_TOKEN in result
        assert "15 triệu" not in result

    def test_redacts_number_followed_by_tr(self, redactor: PIIRedactor):
        """Number followed by tr should be redacted."""
        text = "Lương mong muốn: 20tr"
        result = redactor.redact(text)
        assert REDACTED_TOKEN in result
        assert "20tr" not in result

    def test_redacts_comma_formatted_salary(self, redactor: PIIRedactor):
        """Comma-formatted number >= 1,000,000 should be redacted."""
        text = "Thu nhập: 15,000,000 mỗi tháng"
        result = redactor.redact(text)
        assert REDACTED_TOKEN in result
        assert "15,000,000" not in result

    def test_redacts_dot_formatted_salary(self, redactor: PIIRedactor):
        """Dot-formatted number >= 1,000,000 should be redacted."""
        text = "Lương: 15.000.000 VND/tháng"
        result = redactor.redact(text)
        assert REDACTED_TOKEN in result
        assert "15.000.000" not in result

    def test_does_not_redact_small_formatted_number(self, redactor: PIIRedactor):
        """Comma-formatted number < 1,000,000 should NOT be redacted."""
        text = "Chi phí: 500,000 cho vật tư"
        result = redactor.redact(text)
        assert "500,000" in result

    def test_preserves_surrounding_text_for_salary(self, redactor: PIIRedactor):
        """Text around salary figures should remain intact."""
        text = "Mức lương mong muốn: 25 triệu/tháng, thương lượng"
        result = redactor.redact(text)
        assert "Mức lương mong muốn: " in result
        assert "/tháng, thương lượng" in result

    def test_redacts_formatted_number_with_vnd(self, redactor: PIIRedactor):
        """Formatted number with VND keyword should be redacted."""
        text = "Lương gross: 25,000,000 VND"
        result = redactor.redact(text)
        assert "25,000,000 VND" not in result
        assert REDACTED_TOKEN in result


class TestUnicodeVietnamese:
    """Tests for Unicode Vietnamese text handling."""

    def test_preserves_vietnamese_diacritics(self, redactor: PIIRedactor):
        """Vietnamese diacritics should be preserved in non-PII text."""
        text = "Nguyễn Văn Ân, CCCD: 012345678901, quê quán Đà Nẵng"
        result = redactor.redact(text)
        assert "Nguyễn Văn Ân" in result
        assert "quê quán Đà Nẵng" in result

    def test_handles_dong_symbol(self, redactor: PIIRedactor):
        """The đ (đồng) symbol should be recognized as currency keyword."""
        text = "Mức lương: 20000000đ/tháng"
        result = redactor.redact(text)
        assert REDACTED_TOKEN in result
        assert "20000000đ" not in result

    def test_handles_mixed_vietnamese_and_numbers(self, redactor: PIIRedactor):
        """Mixed Vietnamese text with PII numbers should be handled correctly."""
        text = "Ứng viên Trần Thị Bình, số CMND 012345678901, kinh nghiệm 5 năm"
        result = redactor.redact(text)
        assert "Ứng viên Trần Thị Bình" in result
        assert "012345678901" not in result
        assert "kinh nghiệm 5 năm" in result


class TestOverlappingPatterns:
    """Tests for overlapping pattern handling."""

    def test_no_double_redaction(self, redactor: PIIRedactor):
        """A number matching multiple patterns should only be redacted once."""
        # 12 digits could match both CCCD and bank account patterns
        text = "Số: 012345678901"
        result = redactor.redact(text)
        # Should have exactly one [REDACTED] token, not multiple
        assert result.count(REDACTED_TOKEN) == 1

    def test_adjacent_patterns_redacted_separately(self, redactor: PIIRedactor):
        """Adjacent but non-overlapping patterns should each be redacted."""
        text = "CCCD: 012345678901, STK: 9876543210"
        result = redactor.redact(text)
        assert "012345678901" not in result
        assert "9876543210" not in result
        assert result.count(REDACTED_TOKEN) == 2

    def test_salary_with_large_digit_sequence(self, redactor: PIIRedactor):
        """A salary figure that is also a large digit sequence should be redacted once."""
        text = "Lương: 15000000 VND"
        result = redactor.redact(text)
        # The "15000000 VND" matches salary pattern and "15000000" matches digit pattern
        # Should result in a single redaction
        assert result.count(REDACTED_TOKEN) == 1


class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_string(self, redactor: PIIRedactor):
        """Empty string should return empty string."""
        assert redactor.redact("") == ""

    def test_no_pii_text(self, redactor: PIIRedactor):
        """Text without PII should be returned unchanged."""
        text = "Xin chào, tôi là Nguyễn Văn A, 5 năm kinh nghiệm Python"
        assert redactor.redact(text) == text

    def test_short_numbers_not_redacted(self, redactor: PIIRedactor):
        """Short numbers (< 8 digits) should not be redacted."""
        text = "Điện thoại: 0901234 (7 số)"
        result = redactor.redact(text)
        assert "0901234" in result

    def test_only_pii_text(self, redactor: PIIRedactor):
        """Text that is entirely PII should be fully redacted."""
        text = "012345678901"
        result = redactor.redact(text)
        assert result == REDACTED_TOKEN

    def test_multiline_text(self, redactor: PIIRedactor):
        """PII in multiline text should be redacted across lines."""
        text = "Thông tin:\nCCCD: 012345678901\nLương: 20 triệu\nKỹ năng: Python"
        result = redactor.redact(text)
        assert "012345678901" not in result
        assert "20 triệu" not in result
        assert "Kỹ năng: Python" in result

    def test_case_insensitive_vnd(self, redactor: PIIRedactor):
        """VND keyword matching should be case-insensitive."""
        text = "Salary: 15000000 vnd per month"
        result = redactor.redact(text)
        assert REDACTED_TOKEN in result
        assert "15000000 vnd" not in result
