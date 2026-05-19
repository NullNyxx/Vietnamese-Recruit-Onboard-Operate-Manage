"use client";

import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Plus, Pencil, Trash2 } from "lucide-react";
import type { Position, Department } from "@/lib/api/types";
import {
  listPositions,
  createPosition,
  updatePosition,
  deletePosition,
} from "@/lib/api/positions";
import { listDepartments } from "@/lib/api/departments";

export default function PositionsPage() {
  const [positions, setPositions] = useState<Position[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Add form state
  const [newName, setNewName] = useState("");
  const [newDepartmentId, setNewDepartmentId] = useState("");
  const [adding, setAdding] = useState(false);

  // Edit state
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState("");
  const [editDepartmentId, setEditDepartmentId] = useState("");
  const [saving, setSaving] = useState(false);

  const fetchPositions = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await listPositions();
      setPositions(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load positions");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPositions();
    listDepartments().then(setDepartments).catch(() => {});
  }, [fetchPositions]);

  const getDepartmentName = (departmentId: string | null) => {
    if (!departmentId) return "—";
    const dept = departments.find((d) => d.id === departmentId);
    return dept?.name || "—";
  };

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName.trim()) return;
    setAdding(true);
    setError(null);
    try {
      await createPosition({
        name: newName.trim(),
        department_id: newDepartmentId || undefined,
      });
      setNewName("");
      setNewDepartmentId("");
      await fetchPositions();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create position");
    } finally {
      setAdding(false);
    }
  };

  const handleEdit = (pos: Position) => {
    setEditingId(pos.id);
    setEditName(pos.name);
    setEditDepartmentId(pos.department_id || "");
  };

  const handleCancelEdit = () => {
    setEditingId(null);
    setEditName("");
    setEditDepartmentId("");
  };

  const handleSaveEdit = async (id: string) => {
    if (!editName.trim()) return;
    setSaving(true);
    setError(null);
    try {
      await updatePosition(id, {
        name: editName.trim(),
        department_id: editDepartmentId || undefined,
      });
      setEditingId(null);
      await fetchPositions();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update position");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string, name: string) => {
    if (!window.confirm(`Are you sure you want to delete "${name}"?`)) return;
    setError(null);
    try {
      await deletePosition(id);
      await fetchPositions();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete position");
    }
  };

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-foreground">Positions</h1>
        <p className="text-sm text-muted-foreground">
          Manage your organization&apos;s positions
        </p>
      </div>

      {/* Error */}
      {error && (
        <div className="mb-4 rounded-md bg-destructive/10 p-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {/* Add Form */}
      <form onSubmit={handleAdd} className="mb-4 flex items-center gap-3">
        <input
          type="text"
          placeholder="Position name"
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          className="h-9 w-48 rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          required
        />
        <select
          value={newDepartmentId}
          onChange={(e) => setNewDepartmentId(e.target.value)}
          className="h-9 rounded-md border border-input bg-background px-3 text-sm"
        >
          <option value="">No Department</option>
          {departments.map((d) => (
            <option key={d.id} value={d.id}>
              {d.name}
            </option>
          ))}
        </select>
        <Button type="submit" size="sm" disabled={adding || !newName.trim()}>
          <Plus className="mr-2 h-4 w-4" />
          {adding ? "Adding..." : "Add Position"}
        </Button>
      </form>

      {/* Table */}
      <div className="rounded-md border border-border bg-white">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-muted/50">
              <th className="px-4 py-3 text-left font-medium text-muted-foreground">Name</th>
              <th className="px-4 py-3 text-left font-medium text-muted-foreground">Department</th>
              <th className="px-4 py-3 text-left font-medium text-muted-foreground">Created</th>
              <th className="px-4 py-3 text-left font-medium text-muted-foreground">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={4} className="px-4 py-8 text-center text-muted-foreground">
                  Loading...
                </td>
              </tr>
            ) : positions.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-4 py-8 text-center text-muted-foreground">
                  No positions found
                </td>
              </tr>
            ) : (
              positions.map((pos) =>
                editingId === pos.id ? (
                  <tr key={pos.id} className="border-b border-border last:border-0 bg-muted/20">
                    <td className="px-4 py-2">
                      <input
                        type="text"
                        value={editName}
                        onChange={(e) => setEditName(e.target.value)}
                        className="h-8 w-full rounded-md border border-input bg-background px-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                      />
                    </td>
                    <td className="px-4 py-2">
                      <select
                        value={editDepartmentId}
                        onChange={(e) => setEditDepartmentId(e.target.value)}
                        className="h-8 w-full rounded-md border border-input bg-background px-2 text-sm"
                      >
                        <option value="">No Department</option>
                        {departments.map((d) => (
                          <option key={d.id} value={d.id}>
                            {d.name}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="px-4 py-2 text-muted-foreground">
                      {new Date(pos.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-2">
                      <div className="flex items-center gap-1">
                        <Button
                          size="sm"
                          onClick={() => handleSaveEdit(pos.id)}
                          disabled={saving || !editName.trim()}
                        >
                          {saving ? "Saving..." : "Save"}
                        </Button>
                        <Button variant="ghost" size="sm" onClick={handleCancelEdit}>
                          Cancel
                        </Button>
                      </div>
                    </td>
                  </tr>
                ) : (
                  <tr key={pos.id} className="border-b border-border last:border-0 hover:bg-muted/30">
                    <td className="px-4 py-3 font-medium">{pos.name}</td>
                    <td className="px-4 py-3 text-muted-foreground">
                      {getDepartmentName(pos.department_id)}
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">
                      {new Date(pos.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1">
                        <Button variant="ghost" size="sm" onClick={() => handleEdit(pos)}>
                          <Pencil className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDelete(pos.id, pos.name)}
                          className="text-destructive hover:text-destructive"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </td>
                  </tr>
                )
              )
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
