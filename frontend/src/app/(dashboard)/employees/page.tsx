"use client";

import { useCallback, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { UserPlus, FileSpreadsheet } from "lucide-react";

import { DataTable, type ColumnDef } from "@/components/data-table";
import { Button } from "@/components/ui/button";
import { useEmployees } from "@/hooks/queries/use-employees";
import { useDepartments } from "@/hooks/queries/use-departments";
import { usePositions } from "@/hooks/queries/use-positions";
import type { Employee } from "@/lib/api/types";

interface EmployeeRow extends Record<string, unknown> {
  id: string;
  full_name: string;
  email: string;
  department_name: string;
  position_name: string;
  is_active: boolean;
}

const columns: ColumnDef<EmployeeRow>[] = [
  { key: "full_name", header: "Họ tên" },
  { key: "email", header: "Email" },
  { key: "department_name", header: "Phòng ban" },
  { key: "position_name", header: "Chức vụ" },
  {
    key: "is_active",
    header: "Trạng thái",
    cell: (row) => (
      <span
        className={row.is_active ? "text-green-600" : "text-muted-foreground"}
      >
        {row.is_active ? "Đang làm" : "Đã nghỉ"}
      </span>
    ),
  },
];

export default function EmployeesPage() {
  const router = useRouter();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [search, setSearch] = useState("");

  // React Query — cached, deduplicated, background refetch
  const {
    data: employeesData,
    isLoading,
    error,
  } = useEmployees({
    page,
    page_size: pageSize,
    search: search || undefined,
  });

  const { data: departments = [] } = useDepartments();
  const { data: positions = [] } = usePositions();

  // Map employees to rows with department/position names
  const rows: EmployeeRow[] = useMemo(() => {
    if (!employeesData?.items) return [];

    const deptMap = new Map(departments.map((d) => [d.id, d.name]));
    const posMap = new Map(positions.map((p) => [p.id, p.name]));

    return employeesData.items.map((emp: Employee) => ({
      id: emp.id,
      full_name: emp.full_name,
      email: emp.email,
      department_name: emp.department_id
        ? (deptMap.get(emp.department_id) ?? "—")
        : "—",
      position_name: emp.position_id
        ? (posMap.get(emp.position_id) ?? "—")
        : "—",
      is_active: emp.is_active,
    }));
  }, [employeesData?.items, departments, positions]);

  const handleSearch = useCallback((query: string) => {
    setSearch(query);
    setPage(1);
  }, []);

  const handlePageChange = useCallback((newPage: number) => {
    setPage(newPage);
  }, []);

  const handlePageSizeChange = useCallback((newSize: number) => {
    setPageSize(newSize);
    setPage(1);
  }, []);

  const handleRowClick = useCallback(
    (row: EmployeeRow) => {
      router.push(`/employees/${row.id}`);
    },
    [router],
  );

  const toolbar = (
    <>
      <Link href="/employees/import">
        <Button variant="outline" size="sm">
          <FileSpreadsheet className="mr-2 h-4 w-4" aria-hidden="true" />
          Import Excel
        </Button>
      </Link>
      <Link href="/employees/new">
        <Button size="sm">
          <UserPlus className="mr-2 h-4 w-4" aria-hidden="true" />
          Thêm nhân viên
        </Button>
      </Link>
    </>
  );

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="font-heading text-2xl font-bold">Nhân viên</h1>
        <p className="text-sm text-muted-foreground">
          Quản lý danh sách nhân viên trong tổ chức
        </p>
      </div>

      <DataTable<EmployeeRow>
        columns={columns}
        data={rows}
        loading={isLoading}
        error={error?.message ?? null}
        pagination={{ page, pageSize, total: employeesData?.total ?? 0 }}
        searchPlaceholder="Tìm kiếm theo tên hoặc email..."
        onSearch={handleSearch}
        onPageChange={handlePageChange}
        onPageSizeChange={handlePageSizeChange}
        onRowClick={handleRowClick}
        toolbar={toolbar}
      />
    </div>
  );
}
