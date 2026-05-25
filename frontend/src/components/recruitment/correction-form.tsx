"use client";

import * as React from "react";
import { useForm, useFieldArray } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Loader2, Plus, Trash2 } from "lucide-react";

import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";

import type {
  ParsedCVInput,
  ParsedCVData,
  ValidationError,
} from "@/lib/api/recruitment";

// ---------------------------------------------------------------------------
// Zod Schema
// ---------------------------------------------------------------------------

const experienceItemSchema = z.object({
  company: z.string(),
  role: z.string(),
  duration: z.string(),
});

const educationItemSchema = z.object({
  institution: z.string(),
  degree: z.string(),
  year: z.string(),
});

export const correctionFormSchema = z.object({
  name: z
    .string()
    .min(1, "Họ tên không được để trống")
    .max(200, "Họ tên tối đa 200 ký tự"),
  email: z.string().email("Email không hợp lệ"),
  phone: z.string().max(20, "Số điện thoại tối đa 20 ký tự"),
  skills: z.array(z.string()).max(50, "Tối đa 50 kỹ năng"),
  experience: z
    .array(experienceItemSchema)
    .max(20, "Tối đa 20 mục kinh nghiệm"),
  education: z.array(educationItemSchema).max(10, "Tối đa 10 mục học vấn"),
  summary: z.string().max(500, "Tóm tắt tối đa 500 ký tự"),
});

type CorrectionFormValues = z.infer<typeof correctionFormSchema>;

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface CorrectionFormProps {
  initialData: ParsedCVData | null;
  onSubmit: (data: ParsedCVInput) => Promise<void>;
  loading: boolean;
  serverErrors: ValidationError[] | null;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function CorrectionForm({
  initialData,
  onSubmit,
  loading,
  serverErrors,
}: CorrectionFormProps) {
  const form = useForm<CorrectionFormValues>({
    resolver: zodResolver(correctionFormSchema),
    defaultValues: {
      name: initialData?.name ?? "",
      email: initialData?.email ?? "",
      phone: initialData?.phone ?? "",
      skills: initialData?.skills ?? [],
      experience: initialData?.experience ?? [],
      education: initialData?.education ?? [],
      summary: initialData?.summary ?? "",
    },
  });

  const {
    fields: experienceFields,
    append: appendExperience,
    remove: removeExperience,
  } = useFieldArray({
    control: form.control,
    name: "experience",
  });

  const {
    fields: educationFields,
    append: appendEducation,
    remove: removeEducation,
  } = useFieldArray({
    control: form.control,
    name: "education",
  });

  // Skills managed as comma-separated string in a text input
  const [skillsInput, setSkillsInput] = React.useState(
    (initialData?.skills ?? []).join(", "),
  );

  async function handleFormSubmit(values: CorrectionFormValues) {
    await onSubmit(values);
  }

  // Sync skills input to form value
  function handleSkillsChange(value: string) {
    setSkillsInput(value);
    const skills = value
      .split(",")
      .map((s) => s.trim())
      .filter((s) => s.length > 0);
    form.setValue("skills", skills, { shouldValidate: true });
  }

  // Map server errors to the appropriate fields
  function getServerError(field: string): string | undefined {
    if (!serverErrors) return undefined;
    const error = serverErrors.find((e) => e.field === field);
    return error?.message;
  }

  return (
    <Form {...form}>
      <form
        onSubmit={form.handleSubmit(handleFormSubmit)}
        className="space-y-4"
      >
        {/* Name */}
        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Họ tên</FormLabel>
              <FormControl>
                <Input
                  placeholder="Nhập họ tên..."
                  maxLength={200}
                  {...field}
                />
              </FormControl>
              <FormMessage />
              {getServerError("name") && (
                <p className="text-sm font-medium text-destructive">
                  {getServerError("name")}
                </p>
              )}
            </FormItem>
          )}
        />

        {/* Email */}
        <FormField
          control={form.control}
          name="email"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Email</FormLabel>
              <FormControl>
                <Input type="email" placeholder="Nhập email..." {...field} />
              </FormControl>
              <FormMessage />
              {getServerError("email") && (
                <p className="text-sm font-medium text-destructive">
                  {getServerError("email")}
                </p>
              )}
            </FormItem>
          )}
        />

        {/* Phone */}
        <FormField
          control={form.control}
          name="phone"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Số điện thoại</FormLabel>
              <FormControl>
                <Input
                  placeholder="Nhập số điện thoại..."
                  maxLength={20}
                  {...field}
                />
              </FormControl>
              <FormMessage />
              {getServerError("phone") && (
                <p className="text-sm font-medium text-destructive">
                  {getServerError("phone")}
                </p>
              )}
            </FormItem>
          )}
        />

        {/* Skills */}
        <FormField
          control={form.control}
          name="skills"
          render={() => (
            <FormItem>
              <FormLabel>Kỹ năng</FormLabel>
              <FormControl>
                <Input
                  placeholder="Nhập kỹ năng, phân cách bằng dấu phẩy..."
                  value={skillsInput}
                  onChange={(e) => handleSkillsChange(e.target.value)}
                />
              </FormControl>
              <FormMessage />
              {getServerError("skills") && (
                <p className="text-sm font-medium text-destructive">
                  {getServerError("skills")}
                </p>
              )}
            </FormItem>
          )}
        />

        {/* Experience */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <FormLabel>Kinh nghiệm</FormLabel>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() =>
                appendExperience({ company: "", role: "", duration: "" })
              }
              disabled={experienceFields.length >= 20}
            >
              <Plus className="h-4 w-4 mr-1" />
              Thêm
            </Button>
          </div>
          {form.formState.errors.experience?.message && (
            <p className="text-sm font-medium text-destructive">
              {form.formState.errors.experience.message}
            </p>
          )}
          {getServerError("experience") && (
            <p className="text-sm font-medium text-destructive">
              {getServerError("experience")}
            </p>
          )}
          {experienceFields.length === 0 && (
            <p className="text-sm text-muted-foreground">
              Chưa có mục kinh nghiệm nào
            </p>
          )}
          {experienceFields.map((field, index) => (
            <div
              key={field.id}
              className="grid grid-cols-1 gap-2 rounded-md border p-3 sm:grid-cols-3"
            >
              <FormField
                control={form.control}
                name={`experience.${index}.company`}
                render={({ field }) => (
                  <FormItem>
                    <FormControl>
                      <Input placeholder="Công ty" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name={`experience.${index}.role`}
                render={({ field }) => (
                  <FormItem>
                    <FormControl>
                      <Input placeholder="Vị trí" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <div className="flex items-start gap-2">
                <FormField
                  control={form.control}
                  name={`experience.${index}.duration`}
                  render={({ field }) => (
                    <FormItem className="flex-1">
                      <FormControl>
                        <Input placeholder="Thời gian" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  onClick={() => removeExperience(index)}
                  aria-label={`Xóa kinh nghiệm ${index + 1}`}
                >
                  <Trash2 className="h-4 w-4 text-destructive" />
                </Button>
              </div>
            </div>
          ))}
        </div>

        {/* Education */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <FormLabel>Học vấn</FormLabel>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() =>
                appendEducation({ institution: "", degree: "", year: "" })
              }
              disabled={educationFields.length >= 10}
            >
              <Plus className="h-4 w-4 mr-1" />
              Thêm
            </Button>
          </div>
          {form.formState.errors.education?.message && (
            <p className="text-sm font-medium text-destructive">
              {form.formState.errors.education.message}
            </p>
          )}
          {getServerError("education") && (
            <p className="text-sm font-medium text-destructive">
              {getServerError("education")}
            </p>
          )}
          {educationFields.length === 0 && (
            <p className="text-sm text-muted-foreground">
              Chưa có mục học vấn nào
            </p>
          )}
          {educationFields.map((field, index) => (
            <div
              key={field.id}
              className="grid grid-cols-1 gap-2 rounded-md border p-3 sm:grid-cols-3"
            >
              <FormField
                control={form.control}
                name={`education.${index}.institution`}
                render={({ field }) => (
                  <FormItem>
                    <FormControl>
                      <Input placeholder="Trường/Tổ chức" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name={`education.${index}.degree`}
                render={({ field }) => (
                  <FormItem>
                    <FormControl>
                      <Input placeholder="Bằng cấp" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <div className="flex items-start gap-2">
                <FormField
                  control={form.control}
                  name={`education.${index}.year`}
                  render={({ field }) => (
                    <FormItem className="flex-1">
                      <FormControl>
                        <Input placeholder="Năm" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  onClick={() => removeEducation(index)}
                  aria-label={`Xóa học vấn ${index + 1}`}
                >
                  <Trash2 className="h-4 w-4 text-destructive" />
                </Button>
              </div>
            </div>
          ))}
        </div>

        {/* Summary */}
        <FormField
          control={form.control}
          name="summary"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Tóm tắt</FormLabel>
              <FormControl>
                <Textarea
                  placeholder="Nhập tóm tắt..."
                  maxLength={500}
                  rows={4}
                  {...field}
                />
              </FormControl>
              <FormMessage />
              {getServerError("summary") && (
                <p className="text-sm font-medium text-destructive">
                  {getServerError("summary")}
                </p>
              )}
            </FormItem>
          )}
        />

        {/* Submit */}
        <Button type="submit" disabled={loading}>
          {loading && <Loader2 className="animate-spin mr-2 h-4 w-4" />}
          Lưu chỉnh sửa
        </Button>
      </form>
    </Form>
  );
}
