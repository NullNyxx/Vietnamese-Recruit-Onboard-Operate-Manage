"use client";

import { useRouter } from "next/navigation";
import { EmployeeForm } from "@/components/employee-form";
import { createEmployee } from "@/lib/api/employees";
import type { EmployeeCreateData } from "@/lib/api/types";

export default function NewEmployeePage() {
  const router = useRouter();

  const handleSubmit = async (data: EmployeeCreateData) => {
    await createEmployee(data);
    router.push("/employees");
  };

  return (
    <EmployeeForm
      title="Add Employee"
      submitLabel="Create Employee"
      onSubmit={handleSubmit}
    />
  );
}
