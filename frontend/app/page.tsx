"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "./lib/api";

export default function Dashboard() {
  const [stats, setStats] = useState({ personnel: 0, orders: 0, vehicles: 0, customers: 0 });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([api.getPersonnel(), api.getServiceOrders(), api.getVehicles(), api.getCustomers()])
      .then(([p, o, v, c]) => {
        setStats({ personnel: p.length, orders: o.length, vehicles: v.length, customers: c.length });
      })
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="max-w-5xl">
      <h1 className="text-2xl font-bold mb-2">Dispatch Dashboard</h1>
      <p className="text-muted-foreground mb-8">
        AI-powered workforce scheduling for traffic management operations
      </p>

      {loading ? (
        <div className="text-muted-foreground">Loading...</div>
      ) : (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            <StatCard label="Personnel" value={stats.personnel} />
            <StatCard label="Service Orders" value={stats.orders} />
            <StatCard label="Vehicles" value={stats.vehicles} />
            <StatCard label="Customers" value={stats.customers} />
          </div>

          <div className="bg-card border border-border rounded-lg p-6">
            <h2 className="text-lg font-semibold mb-3">Quick Start</h2>
            <p className="text-muted-foreground text-sm mb-4">
              Run the full dispatch optimization pipeline to assign crews to all service orders.
            </p>
            <Link
              href="/dispatch"
              className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:opacity-90 transition-opacity"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
              </svg>
              Run Dispatch Flow
            </Link>
          </div>
        </>
      )}
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="bg-card border border-border rounded-lg p-4">
      <div className="text-2xl font-bold">{value}</div>
      <div className="text-sm text-muted-foreground">{label}</div>
    </div>
  );
}
