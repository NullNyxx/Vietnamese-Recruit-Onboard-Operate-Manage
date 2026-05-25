"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { Users, Building2, Briefcase, Mail, UserPlus } from "lucide-react";

import { StatCard } from "@/components/stat-card";
import { Button } from "@/components/ui/button";
import {
  employeesApi,
  departmentsApi,
  positionsApi,
  gmailApi,
} from "@/lib/api";

interface DashboardStats {
  employees: number;
  departments: number;
  positions: number;
  unreadEmails: number;
}

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats>({
    employees: 0,
    departments: 0,
    positions: 0,
    unreadEmails: 0,
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchStats() {
      try {
        const [employeesRes, departments, positions] = await Promise.all([
          employeesApi.listEmployees({ page: 1, page_size: 1 }),
          departmentsApi.listDepartments(),
          positionsApi.listPositions(),
        ]);

        // Try to get unread email count from Gmail status
        let unreadEmails = 0;
        try {
          const gmailStatus = await gmailApi.getStatus();
          if (gmailStatus.status === "connected") {
            // TODO: Add a dedicated unread count endpoint when available
            unreadEmails = 0;
          }
        } catch {
          // Gmail not connected or unavailable — show 0
        }

        setStats({
          employees: employeesRes.total,
          departments: departments.length,
          positions: positions.length,
          unreadEmails,
        });
      } catch {
        // On error, keep default values (0)
      } finally {
        setLoading(false);
      }
    }

    fetchStats();
  }, []);

  const statCards = [
    { title: "Nhân viên", value: stats.employees, icon: Users },
    { title: "Phòng ban", value: stats.departments, icon: Building2 },
    { title: "Chức vụ", value: stats.positions, icon: Briefcase },
    { title: "Email chưa đọc", value: stats.unreadEmails, icon: Mail },
  ];

  return (
    <div className="space-y-8">
      {/* Page title */}
      <h1 className="text-3xl font-bold font-heading tracking-tight">
        Tổng quan
      </h1>

      {/* Stat cards grid */}
      <div className="stagger-children grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {statCards.map((card) => (
          <div key={card.title} className="animate-fade-in">
            <StatCard
              title={card.title}
              value={card.value}
              icon={card.icon}
              loading={loading}
            />
          </div>
        ))}
      </div>

      {/* Quick actions */}
      <section className="space-y-4">
        <h2 className="text-xl font-semibold font-heading">Hành động nhanh</h2>
        <div className="flex flex-wrap gap-3">
          <Button asChild>
            <Link href="/employees/new">
              <UserPlus className="h-4 w-4" aria-hidden="true" />
              Thêm nhân viên
            </Link>
          </Button>
          <Button variant="outline" asChild>
            <Link href="/employees">
              <Users className="h-4 w-4" aria-hidden="true" />
              Danh sách nhân viên
            </Link>
          </Button>
          <Button variant="outline" asChild>
            <Link href="/settings/departments">
              <Building2 className="h-4 w-4" aria-hidden="true" />
              Quản lý phòng ban
            </Link>
          </Button>
          <Button variant="outline" asChild>
            <Link href="/settings/positions">
              <Briefcase className="h-4 w-4" aria-hidden="true" />
              Quản lý chức vụ
            </Link>
          </Button>
        </div>
      </section>
    </div>
  );
}
