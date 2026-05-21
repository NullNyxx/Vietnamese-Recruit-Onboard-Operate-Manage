import { describe, it, expect } from "vitest";
import {
  VALID_TRANSITIONS,
  STATUS_LABELS,
  STATUS_COLORS,
  getValidActions,
  formatConfidence,
  formatDate,
  type CandidateStatus,
} from "./recruitment-utils";

describe("recruitment-utils", () => {
  const ALL_STATUSES: CandidateStatus[] = [
    "new",
    "screening",
    "interview_scheduled",
    "interviewed",
    "accepted",
    "rejected",
    "archived",
  ];

  describe("VALID_TRANSITIONS", () => {
    it("defines transitions for all statuses", () => {
      for (const status of ALL_STATUSES) {
        expect(VALID_TRANSITIONS[status]).toBeDefined();
        expect(Array.isArray(VALID_TRANSITIONS[status])).toBe(true);
      }
    });

    it("terminal statuses have no transitions", () => {
      expect(VALID_TRANSITIONS.accepted).toEqual([]);
      expect(VALID_TRANSITIONS.rejected).toEqual([]);
      expect(VALID_TRANSITIONS.archived).toEqual([]);
    });

    it("new status can transition to screening, interview_scheduled, rejected, archived", () => {
      expect(VALID_TRANSITIONS.new).toEqual([
        "screening",
        "interview_scheduled",
        "rejected",
        "archived",
      ]);
    });
  });

  describe("STATUS_LABELS", () => {
    it("provides Vietnamese labels for all statuses", () => {
      for (const status of ALL_STATUSES) {
        expect(STATUS_LABELS[status]).toBeDefined();
        expect(typeof STATUS_LABELS[status]).toBe("string");
        expect(STATUS_LABELS[status].length).toBeGreaterThan(0);
      }
    });

    it("uses correct Vietnamese labels", () => {
      expect(STATUS_LABELS.new).toBe("Mới");
      expect(STATUS_LABELS.accepted).toBe("Đã chấp nhận");
      expect(STATUS_LABELS.rejected).toBe("Đã từ chối");
    });
  });

  describe("STATUS_COLORS", () => {
    it("provides Tailwind classes for all statuses", () => {
      for (const status of ALL_STATUSES) {
        expect(STATUS_COLORS[status]).toBeDefined();
        expect(typeof STATUS_COLORS[status]).toBe("string");
      }
    });

    it("includes dark mode classes for all statuses", () => {
      for (const status of ALL_STATUSES) {
        expect(STATUS_COLORS[status]).toContain("dark:");
      }
    });
  });

  describe("getValidActions", () => {
    it("returns valid transitions for a given status", () => {
      expect(getValidActions("new")).toEqual(VALID_TRANSITIONS.new);
      expect(getValidActions("screening")).toEqual(VALID_TRANSITIONS.screening);
    });

    it("returns empty array for terminal statuses", () => {
      expect(getValidActions("accepted")).toEqual([]);
      expect(getValidActions("rejected")).toEqual([]);
      expect(getValidActions("archived")).toEqual([]);
    });
  });

  describe("formatConfidence", () => {
    it("converts 0 to 0%", () => {
      expect(formatConfidence(0)).toBe("0%");
    });

    it("converts 1 to 100%", () => {
      expect(formatConfidence(1)).toBe("100%");
    });

    it("converts 0.85 to 85%", () => {
      expect(formatConfidence(0.85)).toBe("85%");
    });

    it("rounds to nearest integer", () => {
      expect(formatConfidence(0.856)).toBe("86%");
      expect(formatConfidence(0.854)).toBe("85%");
    });
  });

  describe("formatDate", () => {
    it("formats ISO string to dd/MM/yyyy", () => {
      expect(formatDate("2024-03-15T10:30:00Z")).toBe("15/03/2024");
    });

    it("pads single-digit day and month", () => {
      expect(formatDate("2024-01-05T00:00:00Z")).toBe("05/01/2024");
    });

    it("handles date-only ISO strings", () => {
      expect(formatDate("2023-12-25")).toBe("25/12/2023");
    });
  });
});
