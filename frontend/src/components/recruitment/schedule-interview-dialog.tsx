"use client";

import * as React from "react";
import { Loader2, X } from "lucide-react";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

export interface Interviewer {
  id: string;
  name: string;
}

export interface ScheduleInterviewDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: (data: {
    date: string;
    time: string;
    interviewerIds: string[];
    notes?: string;
  }) => void;
  loading?: boolean;
  interviewers?: Interviewer[];
}

export function ScheduleInterviewDialog({
  open,
  onOpenChange,
  onConfirm,
  loading = false,
  interviewers = [],
}: ScheduleInterviewDialogProps) {
  const [date, setDate] = React.useState("");
  const [time, setTime] = React.useState("");
  const [selectedInterviewers, setSelectedInterviewers] = React.useState<
    string[]
  >([]);
  const [notes, setNotes] = React.useState("");
  const [touched, setTouched] = React.useState(false);

  const dateTimeError = React.useMemo(() => {
    if (!date || !time) return null;
    const selectedDateTime = new Date(`${date}T${time}`);
    const oneHourFromNow = new Date(Date.now() + 60 * 60 * 1000);
    if (selectedDateTime < oneHourFromNow) {
      return "Thời gian phỏng vấn phải cách hiện tại ít nhất 1 giờ";
    }
    return null;
  }, [date, time]);

  const interviewerError = React.useMemo(() => {
    if (selectedInterviewers.length < 1) {
      return "Vui lòng chọn ít nhất 1 người phỏng vấn";
    }
    if (selectedInterviewers.length > 10) {
      return "Tối đa 10 người phỏng vấn";
    }
    return null;
  }, [selectedInterviewers]);

  const isValid =
    date !== "" &&
    time !== "" &&
    !dateTimeError &&
    !interviewerError &&
    selectedInterviewers.length >= 1;

  function handleConfirm() {
    setTouched(true);
    if (isValid) {
      onConfirm({
        date,
        time,
        interviewerIds: selectedInterviewers,
        notes: notes || undefined,
      });
    }
  }

  function handleOpenChange(nextOpen: boolean) {
    if (!nextOpen && !loading) {
      setDate("");
      setTime("");
      setSelectedInterviewers([]);
      setNotes("");
      setTouched(false);
    }
    onOpenChange(nextOpen);
  }

  function toggleInterviewer(id: string) {
    setSelectedInterviewers((prev) => {
      if (prev.includes(id)) {
        return prev.filter((i) => i !== id);
      }
      if (prev.length >= 10) return prev;
      return [...prev, id];
    });
  }

  function removeInterviewer(id: string) {
    setSelectedInterviewers((prev) => prev.filter((i) => i !== id));
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Lên lịch phỏng vấn</DialogTitle>
          <DialogDescription>
            Chọn thời gian và người phỏng vấn cho ứng viên.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Date input */}
          <div className="space-y-2">
            <Label htmlFor="interview-date">Ngày phỏng vấn</Label>
            <Input
              id="interview-date"
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              aria-invalid={touched && !date}
            />
            {touched && !date && (
              <p className="text-xs text-destructive" role="alert">
                Vui lòng chọn ngày phỏng vấn
              </p>
            )}
          </div>

          {/* Time input */}
          <div className="space-y-2">
            <Label htmlFor="interview-time">Giờ phỏng vấn</Label>
            <Input
              id="interview-time"
              type="time"
              value={time}
              onChange={(e) => setTime(e.target.value)}
              aria-invalid={touched && !time}
            />
            {touched && !time && (
              <p className="text-xs text-destructive" role="alert">
                Vui lòng chọn giờ phỏng vấn
              </p>
            )}
            {touched && dateTimeError && (
              <p className="text-xs text-destructive" role="alert">
                {dateTimeError}
              </p>
            )}
          </div>

          {/* Interviewer multi-select */}
          <div className="space-y-2">
            <Label>Người phỏng vấn (1–10)</Label>

            {/* Selected interviewers */}
            {selectedInterviewers.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {selectedInterviewers.map((id) => {
                  const interviewer = interviewers.find((i) => i.id === id);
                  return (
                    <span
                      key={id}
                      className="inline-flex items-center gap-1 rounded-md bg-primary/10 px-2 py-1 text-xs font-medium text-primary"
                    >
                      {interviewer?.name ?? id}
                      <button
                        type="button"
                        onClick={() => removeInterviewer(id)}
                        className="rounded-sm hover:bg-primary/20"
                        aria-label={`Xóa ${interviewer?.name ?? id}`}
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </span>
                  );
                })}
              </div>
            )}

            {/* Interviewer list */}
            <div className="max-h-40 overflow-y-auto rounded-md border p-2">
              {interviewers.length === 0 ? (
                <p className="text-xs text-muted-foreground">
                  Không có người phỏng vấn khả dụng
                </p>
              ) : (
                <div className="space-y-1">
                  {interviewers.map((interviewer) => {
                    const isSelected = selectedInterviewers.includes(
                      interviewer.id
                    );
                    return (
                      <button
                        key={interviewer.id}
                        type="button"
                        onClick={() => toggleInterviewer(interviewer.id)}
                        className={`w-full rounded-sm px-2 py-1.5 text-left text-sm transition-colors hover:bg-accent ${
                          isSelected
                            ? "bg-primary/10 font-medium text-primary"
                            : ""
                        }`}
                        aria-pressed={isSelected}
                      >
                        {interviewer.name}
                      </button>
                    );
                  })}
                </div>
              )}
            </div>

            {touched && interviewerError && (
              <p className="text-xs text-destructive" role="alert">
                {interviewerError}
              </p>
            )}
          </div>

          {/* Notes (optional) */}
          <div className="space-y-2">
            <Label htmlFor="interview-notes">Ghi chú (tùy chọn)</Label>
            <Textarea
              id="interview-notes"
              placeholder="Ghi chú thêm cho buổi phỏng vấn..."
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={3}
            />
          </div>
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => handleOpenChange(false)}
            disabled={loading}
          >
            Hủy
          </Button>
          <Button onClick={handleConfirm} disabled={loading || !isValid}>
            {loading && <Loader2 className="animate-spin" />}
            Lên lịch phỏng vấn
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
