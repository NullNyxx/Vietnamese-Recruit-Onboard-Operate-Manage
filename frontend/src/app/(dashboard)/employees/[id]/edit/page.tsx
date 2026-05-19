"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Trash2 } from "lucide-react";
import { EmployeeForm } from "@/components/employee-form";
import { getEmployee, updateEmployee, deleteEmployee } from "@/lib/api/employees";
import type { Employee, EmployeeCreateData } from "@/lib/api/types";

export default function EditEmployeePage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const [employee, setEmployee] = useState<Employee | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    async function fetchEmployee() {
      try {
        const data = await getEmployee(id);
        setEmployee(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load employee");
      } finally {
        setLoading(false);
      }
    }
    fetchEmployee();
  }, [id]);

  const handleSubmit = async (data: EmployeeCreateData) => {
    await updateEmployee(id, data);
    router.push(`/employees/${id}`);
  };

  const handleDelete = async () => {
    if (!window.confirm("Are you sure you want to delete this employee? This action cannot be undone.")) {
      return;
    }
    setDeleting(true);
    try {
      await deleteEmployee(id);
      router.push("/employees");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete employee");
      setDeleting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-12">
        <p className="text-muted-foreground">Loading employee...</p>
      </div>
    );
  }

  if (error && !employee) {
    return (
      <div className="p-6">
        <div className="rounded-md bg-destructive/10 p-4 text-sm text-destructive">
          {error}
        </div>
      </div>
    );
  }

  return (
    <div>
      <EmployeeForm
        initialData={employee!}
        title="Edit Employee"
        submitLabel="Save Changes"
        onSubmit={handleSubmit}
      />
      {/* Delete section */}
      <div className="mx-6 mb-6 max-w-3xl rounded-md border border-destructive/30 bg-destructive/5 p-6">
        <h2 className="mb-2 text-lg font-semibold text-destructive">Danger Zone</h2>
        <p className="mb-4 text-sm text-muted-foreground">
          Permanently delete this employee and all associated data. This action cannot be undone.
        </p>
        <Button
          variant="destructive"
          onClick={handleDelete}
          disabled={deleting}
        >
          <Trash2 className="mr-2 h-4 w-4" />
          {deleting ? "Deleting..." : "Delete Employee"}
        </Button>
      </div>
    </div>
  );
}
