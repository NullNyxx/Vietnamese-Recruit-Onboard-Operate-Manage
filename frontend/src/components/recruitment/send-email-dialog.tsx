"use client";

import * as React from "react";
import { Loader2 } from "lucide-react";

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
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";

export interface SendEmailDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: (data: { subject: string; body: string }) => void;
  loading?: boolean;
}

export function SendEmailDialog({
  open,
  onOpenChange,
  onConfirm,
  loading = false,
}: SendEmailDialogProps) {
  const [subject, setSubject] = React.useState("");
  const [body, setBody] = React.useState("");
  const [touched, setTouched] = React.useState(false);

  const subjectError = React.useMemo(() => {
    if (!touched) return null;
    if (subject.length === 0) return "Vui lòng nhập tiêu đề email";
    if (subject.length > 200) return `Tối đa 200 ký tự (hiện tại: ${subject.length})`;
    return null;
  }, [subject, touched]);

  const bodyError = React.useMemo(() => {
    if (!touched) return null;
    if (body.length === 0) return "Vui lòng nhập nội dung email";
    if (body.length > 5000) return `Tối đa 5000 ký tự (hiện tại: ${body.length})`;
    return null;
  }, [body, touched]);

  const isValid =
    subject.length >= 1 &&
    subject.length <= 200 &&
    body.length >= 1 &&
    body.length <= 5000;

  function handleConfirm() {
    setTouched(true);
    if (isValid) {
      onConfirm({ subject, body });
    }
  }

  function handleOpenChange(nextOpen: boolean) {
    if (!nextOpen && !loading) {
      setSubject("");
      setBody("");
      setTouched(false);
    }
    onOpenChange(nextOpen);
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Gửi email cho ứng viên</DialogTitle>
          <DialogDescription>
            Soạn email để gửi cho ứng viên.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Subject */}
          <div className="space-y-2">
            <Label htmlFor="email-subject">Tiêu đề</Label>
            <Input
              id="email-subject"
              placeholder="Nhập tiêu đề email..."
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              onBlur={() => setTouched(true)}
              maxLength={200}
              aria-invalid={!!subjectError}
              aria-describedby={subjectError ? "email-subject-error" : undefined}
            />
            <div className="flex justify-between text-xs text-muted-foreground">
              {subjectError ? (
                <span
                  id="email-subject-error"
                  className="text-destructive"
                  role="alert"
                >
                  {subjectError}
                </span>
              ) : (
                <span />
              )}
              <span>{subject.length}/200</span>
            </div>
          </div>

          {/* Body */}
          <div className="space-y-2">
            <Label htmlFor="email-body">Nội dung</Label>
            <Textarea
              id="email-body"
              placeholder="Nhập nội dung email..."
              value={body}
              onChange={(e) => setBody(e.target.value)}
              onBlur={() => setTouched(true)}
              maxLength={5000}
              rows={8}
              aria-invalid={!!bodyError}
              aria-describedby={bodyError ? "email-body-error" : undefined}
            />
            <div className="flex justify-between text-xs text-muted-foreground">
              {bodyError ? (
                <span
                  id="email-body-error"
                  className="text-destructive"
                  role="alert"
                >
                  {bodyError}
                </span>
              ) : (
                <span />
              )}
              <span>{body.length}/5000</span>
            </div>
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
            Gửi email
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
