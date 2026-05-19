"use client";

import { useCallback, useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import {
  Upload,
  FileSpreadsheet,
  CheckCircle,
  XCircle,
  ArrowLeft,
} from "lucide-react";
import type { ImportResult } from "@/lib/api/types";
import { importEmployees } from "@/lib/api/employees";

export default function ImportPage() {
  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ImportResult | null>(null);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile && droppedFile.name.endsWith(".xlsx")) {
      setFile(droppedFile);
      setError(null);
      setResult(null);
    } else {
      setError("Please select a valid .xlsx file");
    }
  }, []);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      if (selectedFile.name.endsWith(".xlsx")) {
        setFile(selectedFile);
        setError(null);
        setResult(null);
      } else {
        setError("Please select a valid .xlsx file");
      }
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    setError(null);
    setResult(null);
    try {
      const importResult = await importEmployees(file);
      setResult(importResult);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Import failed");
    } finally {
      setUploading(false);
    }
  };

  const handleReset = () => {
    setFile(null);
    setError(null);
    setResult(null);
  };

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6 flex items-center gap-4">
        <Link href="/employees">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back
          </Button>
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-foreground">Import Employees</h1>
          <p className="text-sm text-muted-foreground">
            Upload an Excel file (.xlsx) to bulk import employees
          </p>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="mb-4 rounded-md bg-destructive/10 p-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {/* Upload Area */}
      {!result && (
        <div className="rounded-md border border-border bg-white p-6">
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            className={`flex flex-col items-center justify-center rounded-md border-2 border-dashed p-12 transition-colors ${
              dragging
                ? "border-primary bg-primary/5"
                : "border-border hover:border-muted-foreground/50"
            }`}
          >
            {file ? (
              <>
                <FileSpreadsheet className="mb-3 h-12 w-12 text-green-600" />
                <p className="mb-1 text-sm font-medium text-foreground">{file.name}</p>
                <p className="mb-4 text-xs text-muted-foreground">
                  {(file.size / 1024).toFixed(1)} KB
                </p>
                <div className="flex items-center gap-2">
                  <Button onClick={handleUpload} disabled={uploading}>
                    <Upload className="mr-2 h-4 w-4" />
                    {uploading ? "Uploading..." : "Upload & Import"}
                  </Button>
                  <Button variant="outline" onClick={handleReset} disabled={uploading}>
                    Choose Different File
                  </Button>
                </div>
              </>
            ) : (
              <>
                <Upload className="mb-3 h-12 w-12 text-muted-foreground" />
                <p className="mb-1 text-sm font-medium text-foreground">
                  Drag & drop your Excel file here
                </p>
                <p className="mb-4 text-xs text-muted-foreground">
                  or click to browse (only .xlsx files)
                </p>
                <label className="cursor-pointer">
                  <span className="inline-flex items-center justify-center whitespace-nowrap rounded-md border border-input bg-background px-4 py-2 text-sm font-medium ring-offset-background transition-colors hover:bg-accent hover:text-accent-foreground">
                    Select File
                  </span>
                  <input
                    type="file"
                    accept=".xlsx"
                    onChange={handleFileSelect}
                    className="hidden"
                  />
                </label>
              </>
            )}
          </div>
        </div>
      )}

      {/* Results */}
      {result && (
        <div className="space-y-4">
          {/* Summary */}
          <div className="rounded-md border border-border bg-white p-6">
            <h2 className="mb-4 text-lg font-semibold text-foreground">Import Results</h2>
            <div className="grid grid-cols-3 gap-4">
              <div className="rounded-md border border-border p-4 text-center">
                <p className="text-2xl font-bold text-foreground">{result.total_rows}</p>
                <p className="text-sm text-muted-foreground">Total Rows</p>
              </div>
              <div className="rounded-md border border-border p-4 text-center">
                <div className="flex items-center justify-center gap-2">
                  <CheckCircle className="h-5 w-5 text-green-600" />
                  <p className="text-2xl font-bold text-green-600">{result.success_count}</p>
                </div>
                <p className="text-sm text-muted-foreground">Successful</p>
              </div>
              <div className="rounded-md border border-border p-4 text-center">
                <div className="flex items-center justify-center gap-2">
                  <XCircle className="h-5 w-5 text-red-600" />
                  <p className="text-2xl font-bold text-red-600">{result.error_count}</p>
                </div>
                <p className="text-sm text-muted-foreground">Errors</p>
              </div>
            </div>

            {/* Auto-created info */}
            {((result.departments_created ?? 0) > 0 || (result.positions_created ?? 0) > 0) && (
              <div className="mt-4 rounded-md bg-blue-50 p-3 text-sm text-blue-700">
                <p className="font-medium">Auto-created from import:</p>
                <ul className="mt-1 list-inside list-disc">
                  {(result.departments_created ?? 0) > 0 && (
                    <li>{result.departments_created} new department(s)</li>
                  )}
                  {(result.positions_created ?? 0) > 0 && (
                    <li>{result.positions_created} new position(s)</li>
                  )}
                </ul>
              </div>
            )}
          </div>

          {/* Error Table */}
          {result.errors.length > 0 && (
            <div className="rounded-md border border-border bg-white">
              <div className="border-b border-border px-4 py-3">
                <h3 className="font-medium text-foreground">Errors</h3>
              </div>
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border bg-muted/50">
                    <th className="px-4 py-3 text-left font-medium text-muted-foreground w-24">
                      Row
                    </th>
                    <th className="px-4 py-3 text-left font-medium text-muted-foreground">
                      Error Message
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {result.errors.map((err, idx) => (
                    <tr
                      key={idx}
                      className="border-b border-border last:border-0 hover:bg-muted/30"
                    >
                      <td className="px-4 py-3 font-mono text-xs">{err.row}</td>
                      <td className="px-4 py-3 text-destructive">{err.message}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center gap-2">
            <Button variant="outline" onClick={handleReset}>
              Import Another File
            </Button>
            <Link href="/employees">
              <Button>View Employees</Button>
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
