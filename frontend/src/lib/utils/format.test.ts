import { describe, it, expect } from "vitest";
import { formatDateVN, getInitials, validateDateRange } from "./format";

describe("format utilities", () => {
  describe("formatDateVN", () => {
    it("returns '—' for null input", () => {
      expect(formatDateVN(null)).toBe("—");
    });

    it("returns a non-empty string containing digits for valid ISO date", () => {
      const result = formatDateVN("2024-03-15T10:30:00Z");
      expect(result.length).toBeGreaterThan(0);
      expect(result).toMatch(/\d/);
    });

    it("formats date in Vietnamese locale with day, month, year, hour, minute", () => {
      const result = formatDateVN("2024-01-05T14:30:00Z");
      // Vietnamese locale uses dd/MM/yyyy format
      expect(result).toMatch(/\d{2}\/\d{2}\/\d{4}/);
    });

    it("returns '—' for empty string", () => {
      expect(formatDateVN("")).toBe("—");
    });
  });

  describe("getInitials", () => {
    it("returns first two initials uppercase for multi-word name", () => {
      expect(getInitials("Nguyen Van An")).toBe("NV");
    });

    it("returns single initial for single-word name", () => {
      expect(getInitials("Admin")).toBe("A");
    });

    it("returns at most 2 characters", () => {
      const result = getInitials("Tran Thi Bich Ngoc");
      expect(result.length).toBeLessThanOrEqual(2);
      expect(result).toBe("TT");
    });

    it("returns uppercase characters", () => {
      const result = getInitials("nguyen van");
      expect(result).toBe("NV");
    });

    it("handles names with extra spaces gracefully", () => {
      // split on space produces empty strings which are filtered by part[0]
      const result = getInitials("A B");
      expect(result).toBe("AB");
    });
  });

  describe("validateDateRange", () => {
    it("returns true when end date is after start date", () => {
      expect(validateDateRange("2024-01-01", "2024-01-31")).toBe(true);
    });

    it("returns true when end date equals start date", () => {
      expect(validateDateRange("2024-06-15", "2024-06-15")).toBe(true);
    });

    it("returns false when end date is before start date", () => {
      expect(validateDateRange("2024-06-15", "2024-06-01")).toBe(false);
    });

    it("works with ISO datetime strings", () => {
      expect(
        validateDateRange("2024-01-01T00:00:00Z", "2024-01-01T23:59:59Z")
      ).toBe(true);
      expect(
        validateDateRange("2024-01-02T00:00:00Z", "2024-01-01T23:59:59Z")
      ).toBe(false);
    });
  });
});
