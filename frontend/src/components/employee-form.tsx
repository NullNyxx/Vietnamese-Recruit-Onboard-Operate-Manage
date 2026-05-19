"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { ArrowLeft } from "lucide-react";
import type { Employee, EmployeeCreateData, Department, Position } from "@/lib/api/types";
import { listDepartments } from "@/lib/api/departments";
import { listPositions } from "@/lib/api/positions";

interface EmployeeFormProps {
  initialData?: Employee;
  onSubmit: (data: EmployeeCreateData) => Promise<void>;
  title: string;
  submitLabel: string;
}

export function EmployeeForm({ initialData, onSubmit, title, submitLabel }: EmployeeFormProps) {
  const router = useRouter();
  const [departments, setDepartments] = useState<Department[]>([]);
  const [positions, setPositions] = useState<Position[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [formData, setFormData] = useState<EmployeeCreateData>({
    full_name: initialData?.full_name || "",
    email: initialData?.email || "",
    phone: initialData?.phone || "",
    date_of_birth: initialData?.date_of_birth || "",
    gender: initialData?.gender || "",
    address: initialData?.address || "",
    department_id: initialData?.department_id || "",
    position_id: initialData?.position_id || "",
    start_date: initialData?.start_date || "",
    id_number: initialData?.id_number || "",
    tax_code: initialData?.tax_code || "",
    contract_type: initialData?.contract_type || "",
  });

  useEffect(() => {
    listDepartments().then(setDepartments).catch(() => {});
    listPositions().then(setPositions).catch(() => {});
  }, []);

  useEffect(() => {
    if (initialData) {
      setFormData({
        full_name: initialData.full_name,
        email: initialData.email,
        phone: initialData.phone || "",
        date_of_birth: initialData.date_of_birth || "",
        gender: initialData.gender || "",
        address: initialData.address || "",
        department_id: initialData.department_id || "",
        position_id: initialData.position_id || "",
        start_date: initialData.start_date || "",
        id_number: initialData.id_number || "",
        tax_code: initialData.tax_code || "",
        contract_type: initialData.contract_type || "",
      });
    }
  }, [initialData]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);

    // Clean up empty optional fields
    const payload: EmployeeCreateData = { ...formData };
    Object.keys(payload).forEach((key) => {
      const k = key as keyof EmployeeCreateData;
      if (payload[k] === "") {
        delete payload[k];
      }
    });

    try {
      await onSubmit(payload);
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setSubmitting(false);
    }
  };

  const inputClass =
    "h-10 w-full rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50";
  const labelClass = "block text-sm font-medium text-foreground mb-1.5";

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6 flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => router.push("/employees")}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <h1 className="text-2xl font-bold text-foreground">{title}</h1>
      </div>

      {/* Error */}
      {error && (
        <div className="mb-4 rounded-md bg-destructive/10 p-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {/* Form */}
      <form onSubmit={handleSubmit} className="max-w-3xl space-y-6">
        {/* Personal Information */}
        <div className="rounded-md border border-border bg-white p-6">
          <h2 className="mb-4 text-lg font-semibold text-foreground">Personal Information</h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label htmlFor="full_name" className={labelClass}>
                Full Name <span className="text-destructive">*</span>
              </label>
              <input
                id="full_name"
                name="full_name"
                type="text"
                required
                value={formData.full_name}
                onChange={handleChange}
                className={inputClass}
              />
            </div>
            <div>
              <label htmlFor="email" className={labelClass}>
                Email <span className="text-destructive">*</span>
              </label>
              <input
                id="email"
                name="email"
                type="email"
                required
                value={formData.email}
                onChange={handleChange}
                className={inputClass}
              />
            </div>
            <div>
              <label htmlFor="phone" className={labelClass}>Phone</label>
              <input
                id="phone"
                name="phone"
                type="tel"
                value={formData.phone}
                onChange={handleChange}
                className={inputClass}
              />
            </div>
            <div>
              <label htmlFor="date_of_birth" className={labelClass}>Date of Birth</label>
              <input
                id="date_of_birth"
                name="date_of_birth"
                type="date"
                value={formData.date_of_birth}
                onChange={handleChange}
                className={inputClass}
              />
            </div>
            <div>
              <label htmlFor="gender" className={labelClass}>Gender</label>
              <select
                id="gender"
                name="gender"
                value={formData.gender}
                onChange={handleChange}
                className={inputClass}
              >
                <option value="">Select gender</option>
                <option value="male">Male</option>
                <option value="female">Female</option>
                <option value="other">Other</option>
              </select>
            </div>
            <div>
              <label htmlFor="id_number" className={labelClass}>ID Number</label>
              <input
                id="id_number"
                name="id_number"
                type="text"
                value={formData.id_number}
                onChange={handleChange}
                className={inputClass}
              />
            </div>
            <div className="sm:col-span-2">
              <label htmlFor="address" className={labelClass}>Address</label>
              <textarea
                id="address"
                name="address"
                rows={2}
                value={formData.address}
                onChange={handleChange}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50"
              />
            </div>
          </div>
        </div>

        {/* Employment Information */}
        <div className="rounded-md border border-border bg-white p-6">
          <h2 className="mb-4 text-lg font-semibold text-foreground">Employment Information</h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label htmlFor="department_id" className={labelClass}>Department</label>
              <select
                id="department_id"
                name="department_id"
                value={formData.department_id}
                onChange={handleChange}
                className={inputClass}
              >
                <option value="">Select department</option>
                {departments.map((d) => (
                  <option key={d.id} value={d.id}>{d.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="position_id" className={labelClass}>Position</label>
              <select
                id="position_id"
                name="position_id"
                value={formData.position_id}
                onChange={handleChange}
                className={inputClass}
              >
                <option value="">Select position</option>
                {positions.map((p) => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="start_date" className={labelClass}>Start Date</label>
              <input
                id="start_date"
                name="start_date"
                type="date"
                value={formData.start_date}
                onChange={handleChange}
                className={inputClass}
              />
            </div>
            <div>
              <label htmlFor="contract_type" className={labelClass}>Contract Type</label>
              <select
                id="contract_type"
                name="contract_type"
                value={formData.contract_type}
                onChange={handleChange}
                className={inputClass}
              >
                <option value="">Select contract type</option>
                <option value="full_time">Full Time</option>
                <option value="part_time">Part Time</option>
                <option value="intern">Intern</option>
                <option value="contractor">Contractor</option>
              </select>
            </div>
            <div>
              <label htmlFor="tax_code" className={labelClass}>Tax Code</label>
              <input
                id="tax_code"
                name="tax_code"
                type="text"
                value={formData.tax_code}
                onChange={handleChange}
                className={inputClass}
              />
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-3">
          <Button type="submit" disabled={submitting}>
            {submitting ? "Saving..." : submitLabel}
          </Button>
          <Button type="button" variant="outline" onClick={() => router.push("/employees")}>
            Cancel
          </Button>
        </div>
      </form>
    </div>
  );
}
