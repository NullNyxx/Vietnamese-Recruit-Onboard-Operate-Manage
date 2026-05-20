"use client";

import { useCallback, useEffect, useState } from "react";
import { Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { DataTable, type ColumnDef } from "@/components/data-table";
import { listDepartments } from "@/lib/api/departments";
import { listEmployees } from "@/lib/api/employees";

interface DepartmentRow {
  id: string;
  name: string;
  description: string | null;
  employee_count: number;
  [key: string]: unknown;
}

export default function DepartmentsPage() {
  const [departments, setDepartments] = useState<DepartmentRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [depts, employeesRes] = await Promise.all([
        listDepartments(),
        listEmployees({ page: 1, page_size: 100 }),
      ]);

      // Count employees per department
      const countMap: Record<string, number> = {};
      for (const emp of employeesRes.items) {
        if (emp.department_id) {
          countMap[emp.department_id] = (countMap[emp.department_id] || 0) + 1;
        }
      }

      const rows: DepartmentRow[] = depts.map((dept) => ({
        id: dept.id,
        name: dept.name,
        description: dept.description,
        employee_count: countMap[dept.id] || 0,
      }));

      setDepartments(rows);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Không thể tải danh sách phòng ban"
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

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
        data={departments}
        loading={loading}
        error={error}
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
