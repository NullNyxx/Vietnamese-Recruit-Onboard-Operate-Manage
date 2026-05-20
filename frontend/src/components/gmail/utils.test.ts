import { describe, it, expect } from "vitest";
import {
  formatRelativeDate,
  formatFileSize,
  getLabelCategory,
  LABEL_COLORS,
} from "./utils";

// ---------------------------------------------------------------------------
// formatRelativeDate
// ---------------------------------------------------------------------------

describe("formatRelativeDate", () => {
  const now = new Date("2024-06-15T10:30:00.000Z");

  it('returns "Vừa xong" for less than 1 minute ago', () => {
    const date = new Date(now.getTime() - 30 * 1000).toISOString(); // 30 seconds ago
    expect(formatRelativeDate(date, now)).toBe("Vừa xong");
  });

  it('returns "X phút trước" for less than 60 minutes ago', () => {
    const date = new Date(now.getTime() - 5 * 60 * 1000).toISOString(); // 5 minutes ago
    expect(formatRelativeDate(date, now)).toBe("5 phút trước");
  });

  it('returns "1 phút trước" for exactly 1 minute ago', () => {
    const date = new Date(now.getTime() - 60 * 1000).toISOString();
    expect(formatRelativeDate(date, now)).toBe("1 phút trước");
  });

  it('returns "59 phút trước" for 59 minutes ago', () => {
    const date = new Date(now.getTime() - 59 * 60 * 1000).toISOString();
    expect(formatRelativeDate(date, now)).toBe("59 phút trước");
  });

  it('returns "X giờ trước" for less than 24 hours ago', () => {
    const date = new Date(now.getTime() - 3 * 3600 * 1000).toISOString(); // 3 hours ago
    expect(formatRelativeDate(date, now)).toBe("3 giờ trước");
  });

  it('returns "1 giờ trước" for exactly 1 hour ago', () => {
    const date = new Date(now.getTime() - 3600 * 1000).toISOString();
    expect(formatRelativeDate(date, now)).toBe("1 giờ trước");
  });

  it('returns "Hôm qua" for exactly 1 day ago', () => {
    const date = new Date(now.getTime() - 24 * 3600 * 1000).toISOString(); // 24 hours ago
    expect(formatRelativeDate(date, now)).toBe("Hôm qua");
  });

  it('returns "X ngày trước" for 2-6 days ago', () => {
    const date = new Date(now.getTime() - 3 * 24 * 3600 * 1000).toISOString(); // 3 days ago
    expect(formatRelativeDate(date, now)).toBe("3 ngày trước");
  });

  it('returns "6 ngày trước" for 6 days ago', () => {
    const date = new Date(now.getTime() - 6 * 24 * 3600 * 1000).toISOString();
    expect(formatRelativeDate(date, now)).toBe("6 ngày trước");
  });

  it("returns dd/MM/yyyy for 7 or more days ago", () => {
    const date = new Date("2024-06-01T08:00:00.000Z").toISOString(); // 14 days ago
    expect(formatRelativeDate(date, now)).toBe("01/06/2024");
  });

  it("returns dd/MM/yyyy for old dates", () => {
    const date = new Date("2023-01-15T12:00:00.000Z").toISOString();
    expect(formatRelativeDate(date, now)).toBe("15/01/2023");
  });
});

// ---------------------------------------------------------------------------
// formatFileSize
// ---------------------------------------------------------------------------

describe("formatFileSize", () => {
  it("formats bytes correctly", () => {
    expect(formatFileSize(0)).toBe("0 B");
    expect(formatFileSize(512)).toBe("512 B");
    expect(formatFileSize(1023)).toBe("1023 B");
  });

  it("formats kilobytes correctly", () => {
    expect(formatFileSize(1024)).toBe("1.0 KB");
    expect(formatFileSize(1536)).toBe("1.5 KB");
    expect(formatFileSize(10240)).toBe("10.0 KB");
    expect(formatFileSize(1024 * 1024 - 1)).toBe("1024.0 KB");
  });

  it("formats megabytes correctly", () => {
    expect(formatFileSize(1024 * 1024)).toBe("1.0 MB");
    expect(formatFileSize(1.5 * 1024 * 1024)).toBe("1.5 MB");
    expect(formatFileSize(10 * 1024 * 1024)).toBe("10.0 MB");
  });
});

// ---------------------------------------------------------------------------
// getLabelCategory
// ---------------------------------------------------------------------------

describe("getLabelCategory", () => {
  it("extracts category from VroomHR label", () => {
    expect(getLabelCategory("VroomHR/recruitment")).toBe("recruitment");
    expect(getLabelCategory("VroomHR/interview")).toBe("interview");
    expect(getLabelCategory("VroomHR/onboarding")).toBe("onboarding");
    expect(getLabelCategory("VroomHR/processed")).toBe("processed");
  });

  it("handles Vietnamese label names", () => {
    expect(getLabelCategory("VroomHR/Ứng viên")).toBe("Ứng viên");
    expect(getLabelCategory("VroomHR/Phỏng vấn")).toBe("Phỏng vấn");
  });

  it("returns null for non-VroomHR labels", () => {
    expect(getLabelCategory("INBOX")).toBeNull();
    expect(getLabelCategory("SENT")).toBeNull();
    expect(getLabelCategory("IMPORTANT")).toBeNull();
    expect(getLabelCategory("")).toBeNull();
  });

  it("returns null for partial matches", () => {
    expect(getLabelCategory("VroomHR/")).toBeNull();
    expect(getLabelCategory("VroomHR")).toBeNull();
    expect(getLabelCategory("NotVroomHR/recruitment")).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// LABEL_COLORS
// ---------------------------------------------------------------------------

describe("LABEL_COLORS", () => {
  it("has correct colors for processed", () => {
    expect(LABEL_COLORS.processed).toEqual({
      bg: "bg-gray-100",
      text: "text-gray-700",
    });
  });

  it("has correct colors for recruitment", () => {
    expect(LABEL_COLORS.recruitment).toEqual({
      bg: "bg-blue-100",
      text: "text-blue-700",
    });
  });

  it("has correct colors for interview", () => {
    expect(LABEL_COLORS.interview).toEqual({
      bg: "bg-orange-100",
      text: "text-orange-700",
    });
  });

  it("has correct colors for onboarding", () => {
    expect(LABEL_COLORS.onboarding).toEqual({
      bg: "bg-green-100",
      text: "text-green-700",
    });
  });

  it("has all four label categories defined", () => {
    expect(Object.keys(LABEL_COLORS)).toHaveLength(4);
  });
});
