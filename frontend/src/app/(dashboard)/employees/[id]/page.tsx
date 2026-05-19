"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { ArrowLeft, Trash2, Download, FileText, Upload } from "lucide-react";
import type { Employee, EmployeeDocument, Department, Position } from "@/lib/api/types";
import { getEmployee, listDocuments, uploadDocument, downloadDocument, deleteDocument } from "@/lib/api/employees";
import { listDepartments } from "@/lib/api/departments";
import { listPositions } from "@/lib/api/positions";

export default function EmployeeDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const [employee, setEmployee] = useState<Employee | null>(null);
  const [documents, setDocuments] = useState<EmployeeDocument[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [positions, setPositions] = useState<Position[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Upload state
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadType, setUploadType] = useState("contract");
  const [uploadDescription, setUploadDescription] = useState("");
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchData() {
      try {
        const [emp, docs, depts, pos] = await Promise.all([
          getEmployee(id),
          listDocuments(id),
          listDepartments(),
          listPositions(),
        ]);
        setEmployee(emp);
        setDocuments(docs);
        setDepartments(depts);
        setPositions(pos);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load employee");
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, [id]);

  const getDepartmentName = (deptId: string | null) => {
    if (!deptId) return "—";
    return departments.find((d) => d.id === deptId)?.name || "—";
  };

  const getPositionName = (posId: string | null) => {
    if (!posId) return "—";
    return positions.find((p) => p.id === posId)?.name || "—";
  };

  const formatContractType = (type: string | null) => {
    if (!type) return "—";
    return type.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadFile) return;

    setUploading(true);
    setUploadError(null);
    try {
      const doc = await uploadDocument(id, uploadFile, uploadType, uploadDescription || undefined);
      setDocuments((prev) => [...prev, doc]);
      setUploadFile(null);
      setUploadDescription("");
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const handleDownload = async (doc: EmployeeDocument) => {
    try {
      const blob = await downloadDocument(doc.id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = doc.file_name;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch {
      alert("Failed to download document");
    }
  };

  const handleDeleteDocument = async (docId: string) => {
    if (!window.confirm("Are you sure you want to delete this document?")) return;
    try {
      await deleteDocument(docId);
      setDocuments((prev) => prev.filter((d) => d.id !== docId));
    } catch {
      alert("Failed to delete document");
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-12">
        <p className="text-muted-foreground">Loading employee...</p>
      </div>
    );
  }

  if (error || !employee) {
    return (
      <div className="p-6">
        <div className="rounded-md bg-destructive/10 p-4 text-sm text-destructive">
          {error || "Employee not found"}
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => router.push("/employees")}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <h1 className="text-2xl font-bold text-foreground">{employee.full_name}</h1>
            <p className="text-sm text-muted-foreground">{employee.employee_code}</p>
          </div>
        </div>
        <Link href={`/employees/${id}/edit`}>
          <Button>Edit Employee</Button>
        </Link>
      </div>

      {/* Employee Details */}
      <div className="mb-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Personal Info Card */}
        <div className="rounded-md border border-border bg-white p-6">
          <h2 className="mb-4 text-lg font-semibold text-foreground">Personal Information</h2>
          <dl className="space-y-3">
            <DetailRow label="Full Name" value={employee.full_name} />
            <DetailRow label="Email" value={employee.email} />
            <DetailRow label="Phone" value={employee.phone || "—"} />
            <DetailRow label="Date of Birth" value={employee.date_of_birth || "—"} />
            <DetailRow label="Gender" value={employee.gender ? employee.gender.charAt(0).toUpperCase() + employee.gender.slice(1) : "—"} />
            <DetailRow label="ID Number" value={employee.id_number || "—"} />
            <DetailRow label="Address" value={employee.address || "—"} />
          </dl>
        </div>

        {/* Employment Info Card */}
        <div className="rounded-md border border-border bg-white p-6">
          <h2 className="mb-4 text-lg font-semibold text-foreground">Employment Information</h2>
          <dl className="space-y-3">
            <DetailRow label="Department" value={getDepartmentName(employee.department_id)} />
            <DetailRow label="Position" value={getPositionName(employee.position_id)} />
            <DetailRow label="Start Date" value={employee.start_date || "—"} />
            <DetailRow label="Contract Type" value={formatContractType(employee.contract_type)} />
            <DetailRow label="Tax Code" value={employee.tax_code || "—"} />
            <DetailRow
              label="Status"
              value={
                <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                  employee.is_active ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"
                }`}>
                  {employee.is_active ? "Active" : "Inactive"}
                </span>
              }
            />
          </dl>
        </div>
      </div>

      {/* Documents Section */}
      <div className="rounded-md border border-border bg-white p-6">
        <h2 className="mb-4 text-lg font-semibold text-foreground">Documents</h2>

        {/* Document List */}
        {documents.length === 0 ? (
          <p className="mb-4 text-sm text-muted-foreground">No documents uploaded yet.</p>
        ) : (
          <div className="mb-6 space-y-2">
            {documents.map((doc) => (
              <div
                key={doc.id}
                className="flex items-center justify-between rounded-md border border-border p-3"
              >
                <div className="flex items-center gap-3">
                  <FileText className="h-5 w-5 text-muted-foreground" />
                  <div>
                    <p className="text-sm font-medium">{doc.file_name}</p>
                    <p className="text-xs text-muted-foreground">
                      {doc.document_type} • {formatFileSize(doc.file_size)} • {new Date(doc.uploaded_at).toLocaleDateString()}
                    </p>
                    {doc.description && (
                      <p className="text-xs text-muted-foreground">{doc.description}</p>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-1">
                  <Button variant="ghost" size="icon" onClick={() => handleDownload(doc)} title="Download">
                    <Download className="h-4 w-4" />
                  </Button>
                  <Button variant="ghost" size="icon" onClick={() => handleDeleteDocument(doc.id)} title="Delete">
                    <Trash2 className="h-4 w-4 text-destructive" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Upload Form */}
        <form onSubmit={handleUpload} className="rounded-md border border-dashed border-border p-4">
          <h3 className="mb-3 flex items-center gap-2 text-sm font-medium">
            <Upload className="h-4 w-4" />
            Upload Document
          </h3>
          {uploadError && (
            <div className="mb-3 rounded-md bg-destructive/10 p-2 text-xs text-destructive">
              {uploadError}
            </div>
          )}
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <div>
              <label htmlFor="doc_file" className="mb-1 block text-xs font-medium text-muted-foreground">
                File
              </label>
              <input
                id="doc_file"
                type="file"
                onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
                className="h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm file:border-0 file:bg-transparent file:text-sm file:font-medium"
              />
            </div>
            <div>
              <label htmlFor="doc_type" className="mb-1 block text-xs font-medium text-muted-foreground">
                Document Type
              </label>
              <select
                id="doc_type"
                value={uploadType}
                onChange={(e) => setUploadType(e.target.value)}
                className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              >
                <option value="contract">Contract</option>
                <option value="id_card">ID Card</option>
                <option value="cv">CV / Resume</option>
                <option value="certificate">Certificate</option>
                <option value="other">Other</option>
              </select>
            </div>
            <div>
              <label htmlFor="doc_desc" className="mb-1 block text-xs font-medium text-muted-foreground">
                Description (optional)
              </label>
              <input
                id="doc_desc"
                type="text"
                value={uploadDescription}
                onChange={(e) => setUploadDescription(e.target.value)}
                placeholder="Brief description"
                className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              />
            </div>
          </div>
          <div className="mt-3">
            <Button type="submit" size="sm" disabled={!uploadFile || uploading}>
              <Upload className="mr-2 h-3 w-3" />
              {uploading ? "Uploading..." : "Upload"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}

function DetailRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-4">
      <dt className="text-sm text-muted-foreground">{label}</dt>
      <dd className="text-sm font-medium text-foreground text-right">{value}</dd>
    </div>
  );
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
