"use client";

import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Plus, Pencil, Trash2 } from "lucide-react";
import type { Department } from "@/lib/api/types";
import {
  listDepartments,
  createDepartment,
  updateDepartment,
  deleteDepartment,
} from "@/lib/api/departments";

export default function DepartmentsPage() {
  const [departments, setDepartments] = useState<Department[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Add form state
  const [newName, setNewName] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const [adding, setAdding] = useState(false);

  // Edit state
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [saving, setSaving] = useState(false);

  const fetchDepartments = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await listDepartments();
      setDepartments(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load departments");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDepartments();
  }, [fetchDepartments]);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName.trim()) return;
    setAdding(true);
    setError(null);
    try {
      await createDepartment({
        name: newName.trim(),
        description: newDescription.trim() || undefined,
      });
      setNewName("");
      setNewDescription("");
      await fetchDepartments();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create department");
    } finally {
      setAdding(false);
    }
  };

  const handleEdit = (dept: Department) => {
    setEditingId(dept.id);
    setEditName(dept.name);
    setEditDescription(dept.description || "");
  };

  const handleCancelEdit = () => {
    setEditingId(null);
    setEditName("");
    setEditDescription("");
  };

  const handleSaveEdit = async (id: string) => {
    if (!editName.trim()) return;
    setSaving(true);
    setError(null);
    try {
      await updateDepartment(id, {
        name: editName.trim(),
        description: editDescription.trim() || undefined,
      });
      setEditingId(null);
      await fetchDepartments();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update department");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string, name: string) => {
    if (!window.confirm(`Are you sure you want to delete "${name}"?`)) return;
    setError(null);
    try {
      await deleteDepartment(id);
      await fetchDepartments();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete department");
    }
  };

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-foreground">Departments</h1>
        <p className="text-sm text-muted-foreground">
          Manage your organization&apos;s departments
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
          placeholder="Department name"
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          className="h-9 w-48 rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          required
        />
        <input
          type="text"
          placeholder="Description (optional)"
          value={newDescription}
          onChange={(e) => setNewDescription(e.target.value)}
          className="h-9 flex-1 max-w-xs rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
        />
        <Button type="submit" size="sm" disabled={adding || !newName.trim()}>
          <Plus className="mr-2 h-4 w-4" />
          {adding ? "Adding..." : "Add Department"}
        </Button>
      </form>

      {/* Table */}
      <div className="rounded-md border border-border bg-white">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-muted/50">
              <th className="px-4 py-3 text-left font-medium text-muted-foreground">Name</th>
              <th className="px-4 py-3 text-left font-medium text-muted-foreground">Description</th>
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
            ) : departments.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-4 py-8 text-center text-muted-foreground">
                  No departments found
                </td>
              </tr>
            ) : (
              departments.map((dept) =>
                editingId === dept.id ? (
                  <tr key={dept.id} className="border-b border-border last:border-0 bg-muted/20">
                    <td className="px-4 py-2">
                      <input
                        type="text"
                        value={editName}
                        onChange={(e) => setEditName(e.target.value)}
                        className="h-8 w-full rounded-md border border-input bg-background px-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                      />
                    </td>
                    <td className="px-4 py-2">
                      <input
                        type="text"
                        value={editDescription}
                        onChange={(e) => setEditDescription(e.target.value)}
                        className="h-8 w-full rounded-md border border-input bg-background px-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                      />
                    </td>
                    <td className="px-4 py-2 text-muted-foreground">
                      {new Date(dept.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-2">
                      <div className="flex items-center gap-1">
                        <Button
                          size="sm"
                          onClick={() => handleSaveEdit(dept.id)}
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
                  <tr key={dept.id} className="border-b border-border last:border-0 hover:bg-muted/30">
                    <td className="px-4 py-3 font-medium">{dept.name}</td>
                    <td className="px-4 py-3 text-muted-foreground">{dept.description || "—"}</td>
                    <td className="px-4 py-3 text-muted-foreground">
                      {new Date(dept.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1">
                        <Button variant="ghost" size="sm" onClick={() => handleEdit(dept)}>
                          <Pencil className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDelete(dept.id, dept.name)}
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
