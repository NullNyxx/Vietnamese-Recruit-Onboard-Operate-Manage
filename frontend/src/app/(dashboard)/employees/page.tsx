"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Plus, Upload, Search, ChevronLeft, ChevronRight } from "lucide-react";
import type { EmployeeListResponse, Department, Position } from "@/lib/api/types";
import { listEmployees } from "@/lib/api/employees";
import { listDepartments } from "@/lib/api/departments";
import { listPositions } from "@/lib/api/positions";

export default function EmployeesPage() {
  const [data, setData] = useState<EmployeeListResponse | null>(null);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [positions, setPositions] = useState<Position[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [search, setSearch] = useState("");
  const [departmentId, setDepartmentId] = useState("");
  const [positionId, setPositionId] = useState("");
  const [page, setPage] = useState(1);
  const pageSize = 20;

  const fetchEmployees = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await listEmployees({
        page,
        page_size: pageSize,
        search: search || undefined,
        department_id: departmentId || undefined,
        position_id: positionId || undefined,
      });
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load employees");
    } finally {
      setLoading(false);
    }
  }, [page, search, departmentId, positionId]);

  useEffect(() => {
    fetchEmployees();
  }, [fetchEmployees]);

  useEffect(() => {
    listDepartments().then(setDepartments).catch(() => {});
    listPositions().then(setPositions).catch(() => {});
  }, []);

  const totalPages = data ? Math.ceil(data.total / pageSize) : 0;

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchEmployees();
  };

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Employees</h1>
          <p className="text-sm text-muted-foreground">
            Manage your organization&apos;s employees
          </p>
        </div>
        <div className="flex gap-2">
          <Link href="/employees/import">
            <Button variant="outline" size="sm">
              <Upload className="mr-2 h-4 w-4" />
              Import
            </Button>
          </Link>
          <Link href="/employees/new">
            <Button size="sm">
              <Plus className="mr-2 h-4 w-4" />
              Add Employee
            </Button>
          </Link>
        </div>
      </div>

      {/* Filters */}
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <form onSubmit={handleSearch} className="relative flex-1 min-w-[200px] max-w-md">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search by name or email..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="h-9 w-full rounded-md border border-input bg-background pl-9 pr-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          />
        </form>
        <select
          value={departmentId}
          onChange={(e) => { setDepartmentId(e.target.value); setPage(1); }}
          className="h-9 rounded-md border border-input bg-background px-3 text-sm"
        >
          <option value="">All Departments</option>
          {departments.map((d) => (
            <option key={d.id} value={d.id}>{d.name}</option>
          ))}
        </select>
        <select
          value={positionId}
          onChange={(e) => { setPositionId(e.target.value); setPage(1); }}
          className="h-9 rounded-md border border-input bg-background px-3 text-sm"
        >
          <option value="">All Positions</option>
          {positions.map((p) => (
            <option key={p.id} value={p.id}>{p.name}</option>
          ))}
        </select>
      </div>

      {/* Error */}
      {error && (
        <div className="mb-4 rounded-md bg-destructive/10 p-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {/* Table */}
      <div className="rounded-md border border-border bg-white">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-muted/50">
              <th className="px-4 py-3 text-left font-medium text-muted-foreground">Code</th>
              <th className="px-4 py-3 text-left font-medium text-muted-foreground">Name</th>
              <th className="px-4 py-3 text-left font-medium text-muted-foreground">Email</th>
              <th className="px-4 py-3 text-left font-medium text-muted-foreground">Phone</th>
              <th className="px-4 py-3 text-left font-medium text-muted-foreground">Status</th>
              <th className="px-4 py-3 text-left font-medium text-muted-foreground">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-muted-foreground">
                  Loading...
                </td>
              </tr>
            ) : data?.items.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-muted-foreground">
                  No employees found
                </td>
              </tr>
            ) : (
              data?.items.map((emp) => (
                <tr key={emp.id} className="border-b border-border last:border-0 hover:bg-muted/30">
                  <td className="px-4 py-3 font-mono text-xs">{emp.employee_code}</td>
                  <td className="px-4 py-3 font-medium">
                    <Link href={`/employees/${emp.id}`} className="text-primary hover:underline">
                      {emp.full_name}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">{emp.email}</td>
                  <td className="px-4 py-3 text-muted-foreground">{emp.phone || "—"}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                      emp.is_active
                        ? "bg-green-100 text-green-700"
                        : "bg-red-100 text-red-700"
                    }`}>
                      {emp.is_active ? "Active" : "Inactive"}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <Link href={`/employees/${emp.id}/edit`}>
                      <Button variant="ghost" size="sm">Edit</Button>
                    </Link>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="mt-4 flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            Showing {((page - 1) * pageSize) + 1}–{Math.min(page * pageSize, data?.total || 0)} of {data?.total || 0}
          </p>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page <= 1}
              onClick={() => setPage(page - 1)}
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <span className="text-sm">Page {page} of {totalPages}</span>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= totalPages}
              onClick={() => setPage(page + 1)}
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
