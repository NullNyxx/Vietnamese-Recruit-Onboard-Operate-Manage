"use client";

import { useMemo } from "react";
import { Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { DataTable, type ColumnDef } from "@/components/data-table";
import { useDepartments } from "@/hooks/queries/use-departments";
import { useEmployees } from "@/hooks/queries/use-employees";

interface DepartmentRow {
  id: string;
  name: string;
  description: string | null;
  employee_count: number;
  [key: string]: unknown;
}

export default function DepartmentsPage() {
  const {
    data: departments = [],
    isLoading: deptsLoading,
    error: deptsError,
  } = useDepartments();
  const {
    data: employeesData,
    isLoading: empsLoading,
    error: empsError,
  } = useEmployees({
    page: 1,
    page_size: 100,
  });

  const loading = deptsLoading || empsLoading;
  const error = deptsError ?? empsError;

  const rows: DepartmentRow[] = useMemo(() => {
    if (!departments.length) return [];

    // Count employees per department
    const countMap: Record<string, number> = {};
    if (employeesData?.items) {
      for (const emp of employeesData.items) {
        if (emp.department_id) {
          countMap[emp.department_id] = (countMap[emp.department_id] || 0) + 1;
        }
      }
    }

    return departments.map((dept) => ({
      id: dept.id,
      name: dept.name,
      description: dept.description,
      employee_count: countMap[dept.id] || 0,
    }));
  }, [departments, employeesData?.items]);

  const columns: ColumnDef<DepartmentRow>[] = [
    {
      key: "name",
      header: "Tên phòng ban",
    },
    {
      key: "description",
      header: "Mô tả",
      cell: (row) => row.description || "—",
    },
    {
      key: "employee_count",
      header: "Số nhân viên",
      cell: (row) => (row.employee_count > 0 ? row.employee_count : "—"),
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="font-heading text-2xl font-bold text-foreground">
          Phòng ban
        </h1>
        <p className="text-sm text-muted-foreground">
          Quản lý danh sách phòng ban trong tổ chức
        </p>
      </div>

      {/* DataTable */}
      <DataTable
        columns={columns}
        data={rows}
        loading={loading}
        error={error?.message ?? null}
        toolbar={
          <Button size="sm">
            <Plus className="mr-2 h-4 w-4" aria-hidden="true" />
            Thêm mới
          </Button>
        }
      />
    </div>
  );
}
