"use client";

import * as React from "react";
import { CalendarIcon, X } from "lucide-react";
import { format, isBefore, startOfDay } from "date-fns";

import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Calendar } from "@/components/ui/calendar";
import { cn } from "@/lib/utils";
import { STATUS_LABELS, type CandidateStatus } from "@/lib/recruitment-utils";

// --- Types ---

export interface CandidateFilters {
  search: string;
  status: CandidateStatus | "all";
  dateFrom: Date | undefined;
  dateTo: Date | undefined;
  minConfidence: number; // 0-100 in UI
  skills: string;
}

export interface CandidateFilterChangePayload {
  search?: string;
  status?: CandidateStatus;
  date_from?: string; // YYYY-MM-DD
  date_to?: string; // YYYY-MM-DD
  min_confidence?: number; // 0.0-1.0 decimal for API
  skills?: string; // comma-separated
}

export interface CandidateFilterPanelProps {
  onFilterChange: (filters: CandidateFilterChangePayload) => void;
}

// --- Constants ---

const DEFAULT_FILTERS: CandidateFilters = {
  search: "",
  status: "all",
  dateFrom: undefined,
  dateTo: undefined,
  minConfidence: 0,
  skills: "",
};

const STATUS_OPTIONS: { value: CandidateStatus | "all"; label: string }[] = [
  { value: "all", label: "Tất cả" },
  ...Object.entries(STATUS_LABELS).map(([value, label]) => ({
    value: value as CandidateStatus,
    label,
  })),
];

// --- Helper functions ---

function formatDateDisplay(date: Date | undefined): string {
  if (!date) return "";
  return format(date, "dd/MM/yyyy");
}

export function formatDateForApi(date: Date | undefined): string | undefined {
  if (!date) return undefined;
  return format(date, "yyyy-MM-dd");
}

/**
 * Validates skills input: comma-separated, max 10 items, max 50 chars each.
 * Returns the trimmed, non-empty skills joined by commas, or undefined if empty.
 */
export function parseSkills(input: string): string | undefined {
  if (!input.trim()) return undefined;
  const items = input
    .split(",")
    .map((s) => s.trim())
    .filter((s) => s.length > 0)
    .slice(0, 10)
    .map((s) => s.slice(0, 50));
  return items.length > 0 ? items.join(",") : undefined;
}

/**
 * Validates that dateFrom is not after dateTo.
 */
export function isDateRangeInvalid(
  dateFrom: Date | undefined,
  dateTo: Date | undefined,
): boolean {
  if (!dateFrom || !dateTo) return false;
  return isBefore(startOfDay(dateTo), startOfDay(dateFrom));
}

// --- Component ---

export function CandidateFilterPanel({
  onFilterChange,
}: CandidateFilterPanelProps) {
  const [filters, setFilters] =
    React.useState<CandidateFilters>(DEFAULT_FILTERS);
  const [dateRangeError, setDateRangeError] = React.useState<string | null>(
    null,
  );
  const searchTimeoutRef = React.useRef<ReturnType<typeof setTimeout> | null>(
    null,
  );

  // Build and emit the filter payload
  const emitFilterChange = React.useCallback(
    (updatedFilters: CandidateFilters) => {
      // Validate date range
      if (isDateRangeInvalid(updatedFilters.dateFrom, updatedFilters.dateTo)) {
        setDateRangeError("Ngày bắt đầu phải trước ngày kết thúc");
        return;
      }
      setDateRangeError(null);

      const payload: CandidateFilterChangePayload = {};

      if (updatedFilters.search) {
        payload.search = updatedFilters.search;
      }
      if (updatedFilters.status !== "all") {
        payload.status = updatedFilters.status;
      }
      if (updatedFilters.dateFrom) {
        payload.date_from = formatDateForApi(updatedFilters.dateFrom);
      }
      if (updatedFilters.dateTo) {
        payload.date_to = formatDateForApi(updatedFilters.dateTo);
      }
      if (updatedFilters.minConfidence > 0) {
        payload.min_confidence = updatedFilters.minConfidence / 100;
      }
      const parsedSkills = parseSkills(updatedFilters.skills);
      if (parsedSkills) {
        payload.skills = parsedSkills;
      }

      onFilterChange(payload);
    },
    [onFilterChange],
  );

  // Debounced search handler
  const handleSearchChange = React.useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const value = e.target.value.slice(0, 100);
      const updated = { ...filters, search: value };
      setFilters(updated);

      if (searchTimeoutRef.current) {
        clearTimeout(searchTimeoutRef.current);
      }
      searchTimeoutRef.current = setTimeout(() => {
        emitFilterChange(updated);
      }, 300);
    },
    [filters, emitFilterChange],
  );

  // Cleanup timeout on unmount
  React.useEffect(() => {
    return () => {
      if (searchTimeoutRef.current) {
        clearTimeout(searchTimeoutRef.current);
      }
    };
  }, []);

  // Status change handler
  const handleStatusChange = React.useCallback(
    (value: string) => {
      const updated = { ...filters, status: value as CandidateStatus | "all" };
      setFilters(updated);
      emitFilterChange(updated);
    },
    [filters, emitFilterChange],
  );

  // Date from change handler
  const handleDateFromSelect = React.useCallback(
    (date: Date | undefined) => {
      const updated = { ...filters, dateFrom: date };
      setFilters(updated);
      emitFilterChange(updated);
    },
    [filters, emitFilterChange],
  );

  // Date to change handler
  const handleDateToSelect = React.useCallback(
    (date: Date | undefined) => {
      const updated = { ...filters, dateTo: date };
      setFilters(updated);
      emitFilterChange(updated);
    },
    [filters, emitFilterChange],
  );

  // Confidence slider handler
  const handleConfidenceChange = React.useCallback(
    (value: number[]) => {
      const updated = { ...filters, minConfidence: value[0] };
      setFilters(updated);
      emitFilterChange(updated);
    },
    [filters, emitFilterChange],
  );

  // Skills input handler
  const handleSkillsChange = React.useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const value = e.target.value;
      const updated = { ...filters, skills: value };
      setFilters(updated);
      emitFilterChange(updated);
    },
    [filters, emitFilterChange],
  );

  // Clear all filters
  const handleClearFilters = React.useCallback(() => {
    setFilters(DEFAULT_FILTERS);
    setDateRangeError(null);
    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current);
    }
    onFilterChange({});
  }, [onFilterChange]);

  return (
    <div
      className="space-y-4 rounded-lg border p-4"
      role="search"
      aria-label="Bộ lọc ứng viên"
    >
      {/* Row 1: Search + Status */}
      <div className="grid gap-4 sm:grid-cols-2">
        {/* Search input */}
        <div className="space-y-2">
          <Label htmlFor="filter-search">Tìm kiếm</Label>
          <Input
            id="filter-search"
            type="text"
            placeholder="Tìm kiếm theo tên, email, số điện thoại..."
            value={filters.search}
            onChange={handleSearchChange}
            maxLength={100}
            aria-label="Tìm kiếm theo tên, email, số điện thoại"
          />
        </div>

        {/* Status dropdown */}
        <div className="space-y-2">
          <Label htmlFor="filter-status">Trạng thái</Label>
          <Select value={filters.status} onValueChange={handleStatusChange}>
            <SelectTrigger id="filter-status" aria-label="Lọc theo trạng thái">
              <SelectValue placeholder="Tất cả" />
            </SelectTrigger>
            <SelectContent>
              {STATUS_OPTIONS.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Row 2: Date range */}
      <div className="grid gap-4 sm:grid-cols-2">
        {/* Date from */}
        <div className="space-y-2">
          <Label htmlFor="filter-date-from">Từ ngày</Label>
          <Popover>
            <PopoverTrigger asChild>
              <Button
                id="filter-date-from"
                variant="outline"
                className={cn(
                  "w-full justify-start text-left font-normal",
                  !filters.dateFrom && "text-muted-foreground",
                )}
                aria-label="Chọn ngày bắt đầu"
              >
                <CalendarIcon className="mr-2 h-4 w-4" />
                {filters.dateFrom
                  ? formatDateDisplay(filters.dateFrom)
                  : "dd/MM/yyyy"}
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-auto p-0" align="start">
              <Calendar
                mode="single"
                selected={filters.dateFrom}
                onSelect={handleDateFromSelect}
              />
            </PopoverContent>
          </Popover>
        </div>

        {/* Date to */}
        <div className="space-y-2">
          <Label htmlFor="filter-date-to">Đến ngày</Label>
          <Popover>
            <PopoverTrigger asChild>
              <Button
                id="filter-date-to"
                variant="outline"
                className={cn(
                  "w-full justify-start text-left font-normal",
                  !filters.dateTo && "text-muted-foreground",
                )}
                aria-label="Chọn ngày kết thúc"
              >
                <CalendarIcon className="mr-2 h-4 w-4" />
                {filters.dateTo
                  ? formatDateDisplay(filters.dateTo)
                  : "dd/MM/yyyy"}
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-auto p-0" align="start">
              <Calendar
                mode="single"
                selected={filters.dateTo}
                onSelect={handleDateToSelect}
              />
            </PopoverContent>
          </Popover>
        </div>
      </div>

      {/* Date range error */}
      {dateRangeError && (
        <p className="text-sm text-destructive" role="alert">
          {dateRangeError}
        </p>
      )}

      {/* Row 3: Confidence slider + Skills */}
      <div className="grid gap-4 sm:grid-cols-2">
        {/* Confidence slider */}
        <div className="space-y-2">
          <Label htmlFor="filter-confidence">
            Độ tin cậy tối thiểu: {filters.minConfidence}%
          </Label>
          <Slider
            id="filter-confidence"
            min={0}
            max={100}
            step={1}
            value={[filters.minConfidence]}
            onValueChange={handleConfidenceChange}
            aria-label="Lọc theo độ tin cậy tối thiểu"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={filters.minConfidence}
          />
        </div>

        {/* Skills input */}
        <div className="space-y-2">
          <Label htmlFor="filter-skills">Kỹ năng</Label>
          <Input
            id="filter-skills"
            type="text"
            placeholder="Nhập kỹ năng, phân cách bằng dấu phẩy..."
            value={filters.skills}
            onChange={handleSkillsChange}
            aria-label="Lọc theo kỹ năng (phân cách bằng dấu phẩy, tối đa 10 kỹ năng)"
          />
        </div>
      </div>

      {/* Row 4: Clear button */}
      <div className="flex justify-end">
        <Button
          variant="outline"
          size="sm"
          onClick={handleClearFilters}
          aria-label="Xóa tất cả bộ lọc"
        >
          <X className="mr-1 h-4 w-4" />
          Xóa bộ lọc
        </Button>
      </div>
    </div>
  );
}
