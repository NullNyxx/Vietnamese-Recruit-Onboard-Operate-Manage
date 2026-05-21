"use client";

import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { RefreshCw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import WhitelistTable from "@/components/admin/whitelist-table";
import WhitelistAddForm from "@/components/admin/whitelist-add-form";
import {
  listWhitelist,
  addWhitelistEntry,
  removeWhitelistEntry,
  type WhitelistEntry,
} from "@/lib/api/admin";

// ---------------------------------------------------------------------------
// Page Component
// ---------------------------------------------------------------------------

export default function WhitelistPage() {
  const [entries, setEntries] = useState<WhitelistEntry[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchEntries = useCallback(async () => {
    setLoading(true);
    try {
      const response = await listWhitelist();
      setEntries(response.items);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Không thể tải whitelist";
      toast.error(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchEntries();
  }, [fetchEntries]);

  const handleAdd = useCallback(
    async (value: string) => {
      try {
        await addWhitelistEntry(value);
        toast.success(`Đã thêm "${value}" vào whitelist`);
        await fetchEntries();
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Không thể thêm mục";
        toast.error(message);
        throw err; // Re-throw so the form knows submission failed
      }
    },
    [fetchEntries]
  );

  const handleDelete = useCallback(
    async (id: string) => {
      try {
        await removeWhitelistEntry(id);
        toast.success("Đã xóa mục khỏi whitelist");
        await fetchEntries();
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Không thể xóa mục";
        toast.error(message);
      }
    },
    [fetchEntries]
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-heading text-2xl font-bold text-foreground">
            Whitelist
          </h1>
          <p className="text-sm text-muted-foreground">
            Quản lý danh sách email và domain được phép đăng nhập
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={fetchEntries}
          disabled={loading}
        >
          <RefreshCw
            className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`}
            aria-hidden="true"
          />
          Làm mới
        </Button>
      </div>

      {/* Add Form */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Thêm mục mới</CardTitle>
        </CardHeader>
        <CardContent>
          <WhitelistAddForm onAdd={handleAdd} />
        </CardContent>
      </Card>

      {/* Table */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">
            Danh sách whitelist
            {!loading && (
              <span className="ml-2 text-sm font-normal text-muted-foreground">
                ({entries.length} mục)
              </span>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div aria-live="polite" aria-atomic="true">
            <WhitelistTable
              entries={entries}
              loading={loading}
              onDelete={handleDelete}
            />
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
