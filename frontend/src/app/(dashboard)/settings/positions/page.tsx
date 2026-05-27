"use client";

import { useMemo } from "react";
import { Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { DataTable, type ColumnDef } from "@/components/data-table";
import { usePositions } from "@/hooks/queries/use-positions";
import { useDepartments } from "@/hooks/queries/use-departments";

interface PositionRow {
  id: string;
  name: string;
  department_name: string;
  description: string;
  [key: string]: unknown;
}

export default function PositionsPage() {
  const {
    data: positions = [],
    isLoading: posLoading,
    error: posError,
  } = usePositions();
  const {
    data: departments = [],
    isLoading: deptsLoading,
    error: deptsError,
  } = useDepartments();

  const loading = posLoading || deptsLoading;
  const error = posError ?? deptsError;

  const rows: PositionRow[] = useMemo(() => {
    if (!positions.length) return [];

    // Build department lookup map
    const deptMap: Record<string, string> = {};
    for (const dept of departments) {
      deptMap[dept.id] = dept.name;
    }

    return positions.map((pos) => ({
      id: pos.id,
      name: pos.name,
      department_name: pos.department_id
        ? deptMap[pos.department_id] || "—"
        : "—",
      description: "—",
    }));
  }, [positions, departments]);

  const columns: ColumnDef<PositionRow>[] = [
    {
      key: "name",
      header: "Tên chức vụ",
    },
    {
      key: "department_name",
      header: "Phòng ban",
    },
    {
      key: "description",
      header: "Mô tả",
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="font-heading text-2xl font-bold text-foreground">
          Chức vụ
        </h1>
        <p className="text-sm text-muted-foreground">
          Quản lý danh sách chức vụ trong tổ chức
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
