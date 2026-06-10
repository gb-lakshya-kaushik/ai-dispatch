"use client";

import { useEffect, useState } from "react";
import { api, type Personnel } from "../lib/api";

export default function PersonnelPage() {
  const [personnel, setPersonnel] = useState<Personnel[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getPersonnel().then(setPersonnel).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="text-muted-foreground">Loading personnel...</div>;

  return (
    <div className="max-w-6xl">
      <h1 className="text-2xl font-bold mb-2">Personnel Roster</h1>
      <p className="text-muted-foreground mb-6">
        {personnel.length} Traffic Controllers available for assignment
      </p>

      <div className="bg-card border border-border rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-muted">
              <tr>
                <th className="px-4 py-3 text-left font-medium">ID</th>
                <th className="px-4 py-3 text-left font-medium">Name</th>
                <th className="px-4 py-3 text-left font-medium">Type</th>
                <th className="px-4 py-3 text-left font-medium">Skills</th>
                <th className="px-4 py-3 text-left font-medium">Driver</th>
                <th className="px-4 py-3 text-right font-medium">Rate</th>
                <th className="px-4 py-3 text-right font-medium">Hours YTD</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {personnel.map((p) => (
                <tr key={p.id} className="hover:bg-accent/50 transition-colors">
                  <td className="px-4 py-3 font-mono text-xs">{p.id}</td>
                  <td className="px-4 py-3 font-medium">{p.name}</td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${
                        p.type === "TC"
                          ? "bg-blue-100 text-blue-800"
                          : "bg-green-100 text-green-800"
                      }`}
                    >
                      {p.type}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-1">
                      {p.skills.map((s) => (
                        <span key={s.id} className="inline-flex px-1.5 py-0.5 bg-muted rounded text-xs">
                          {s.name.replace("Installer ", "").replace(" Closure", "")}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="px-4 py-3 font-mono text-xs">{p.driver_class || "—"}</td>
                  <td className="px-4 py-3 text-right">${p.hourly_rate}</td>
                  <td className="px-4 py-3 text-right">{p.hours_worked_ytd}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
