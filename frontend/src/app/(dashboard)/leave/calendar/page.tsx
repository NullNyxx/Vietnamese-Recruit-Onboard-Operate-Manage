"use client";

import { useState, useEffect } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { leaveApi } from "@/lib/api";
import type { LeaveRequest } from "@/lib/api/leave";

const DAY_NAMES = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"];

const statusColors: Record<string, string> = {
  approved: "bg-green-100 text-green-800",
  pending: "bg-yellow-100 text-yellow-800",
};

function getDaysInMonth(year: number, month: number): number {
  return new Date(year, month, 0).getDate();
}

function getFirstDayOfMonth(year: number, month: number): number {
  // 0 = Sunday, convert to Monday-based (0 = Monday)
  const day = new Date(year, month - 1, 1).getDay();
  return day === 0 ? 6 : day - 1;
}

export default function LeaveCalendarPage() {
  const [year, setYear] = useState(2026);
  const [month, setMonth] = useState(5);
  const [requests, setRequests] = useState<LeaveRequest[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchLeaveRequests();
  }, [year, month]);

  async function fetchLeaveRequests() {
    setLoading(true);
    try {
      const data = await leaveApi.listRequests({ page: 1, page_size: 100 });
      // Filter to approved/pending requests that overlap with current month
      const monthStart = new Date(year, month - 1, 1);
      const monthEnd = new Date(year, month, 0);

      const filtered = data.items.filter((req) => {
        if (req.status !== "approved" && req.status !== "pending") return false;
        const start = new Date(req.start_date);
        const end = new Date(req.end_date);
        return start <= monthEnd && end >= monthStart;
      });
      setRequests(filtered);
    } catch {
      // Handle error silently
    } finally {
      setLoading(false);
    }
  }

  function getRequestsForDay(day: number): LeaveRequest[] {
    const dateStr = `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
    const checkDate = new Date(dateStr);

    return requests.filter((req) => {
      const start = new Date(req.start_date);
      const end = new Date(req.end_date);
      return checkDate >= start && checkDate <= end;
    });
  }

  function prevMonth() {
    if (month === 1) {
      setMonth(12);
      setYear(year - 1);
    } else {
      setMonth(month - 1);
    }
  }

  function nextMonth() {
    if (month === 12) {
      setMonth(1);
      setYear(year + 1);
    } else {
      setMonth(month + 1);
    }
  }

  const daysInMonth = getDaysInMonth(year, month);
  const firstDay = getFirstDayOfMonth(year, month);

  // Build calendar grid
  const calendarCells: (number | null)[] = [];
  for (let i = 0; i < firstDay; i++) {
    calendarCells.push(null);
  }
  for (let d = 1; d <= daysInMonth; d++) {
    calendarCells.push(d);
  }

  const monthNames = [
    "Tháng 1", "Tháng 2", "Tháng 3", "Tháng 4",
    "Tháng 5", "Tháng 6", "Tháng 7", "Tháng 8",
    "Tháng 9", "Tháng 10", "Tháng 11", "Tháng 12",
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight">Lịch Nghỉ Phép</h1>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <Button variant="outline" size="sm" onClick={prevMonth}>
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <CardTitle>
              {monthNames[month - 1]} {year}
            </CardTitle>
            <Button variant="outline" size="sm" onClick={nextMonth}>
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {loading ? (
            <p className="text-muted-foreground">Đang tải...</p>
          ) : (
            <div className="grid grid-cols-7 gap-1">
              {/* Day headers */}
              {DAY_NAMES.map((name) => (
                <div
                  key={name}
                  className="text-center text-sm font-medium text-muted-foreground py-2"
                >
                  {name}
                </div>
              ))}

              {/* Calendar cells */}
              {calendarCells.map((day, idx) => {
                if (day === null) {
                  return <div key={`empty-${idx}`} className="min-h-[80px]" />;
                }

                const dayRequests = getRequestsForDay(day);
                const isWeekend =
                  new Date(year, month - 1, day).getDay() === 0 ||
                  new Date(year, month - 1, day).getDay() === 6;

                return (
                  <div
                    key={day}
                    className={`min-h-[80px] border rounded-md p-1 ${
                      isWeekend ? "bg-gray-50" : "bg-white"
                    }`}
                  >
                    <div className="text-xs font-medium text-right mb-1">
                      {day}
                    </div>
                    <div className="space-y-0.5">
                      {dayRequests.slice(0, 3).map((req) => (
                        <Badge
                          key={req.id}
                          className={`text-[10px] px-1 py-0 block truncate ${
                            statusColors[req.status] || ""
                          }`}
                        >
                          {req.employee_id.slice(0, 6)}
                        </Badge>
                      ))}
                      {dayRequests.length > 3 && (
                        <span className="text-[10px] text-muted-foreground">
                          +{dayRequests.length - 3} người
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Legend */}
      <Card>
        <CardContent className="pt-4">
          <div className="flex gap-4 text-sm">
            <div className="flex items-center gap-1">
              <Badge className="bg-green-100 text-green-800">Đã duyệt</Badge>
            </div>
            <div className="flex items-center gap-1">
              <Badge className="bg-yellow-100 text-yellow-800">Chờ duyệt</Badge>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
