"use client";

import { useEffect, useState } from "react";
import { api, type ServiceOrder } from "../lib/api";

const closureColors: Record<string, string> = {
  single_lane: "bg-blue-100 text-blue-800",
  multi_lane: "bg-purple-100 text-purple-800",
  road_closure: "bg-red-100 text-red-800",
  flagging: "bg-yellow-100 text-yellow-800",
  shoulder_closure: "bg-orange-100 text-orange-800",
  lane_shift: "bg-teal-100 text-teal-800",
};

export default function ServiceOrdersPage() {
  const [orders, setOrders] = useState<ServiceOrder[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getServiceOrders().then(setOrders).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="text-muted-foreground">Loading service orders...</div>;

  return (
    <div className="max-w-6xl">
      <h1 className="text-2xl font-bold mb-2">Service Orders</h1>
      <p className="text-muted-foreground mb-6">{orders.length} orders for scheduling</p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {orders.map((o) => (
          <div key={o.id} className="bg-card border border-border rounded-lg p-4">
            <div className="flex items-start justify-between mb-2">
              <div>
                <span className="font-mono text-xs text-muted-foreground">{o.id}</span>
                <h3 className="font-semibold">{o.customer_name}</h3>
              </div>
              <span className="text-xs font-medium px-2 py-0.5 bg-muted rounded">
                Priority {o.priority}
              </span>
            </div>

            <span
              className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium mb-3 ${
                closureColors[o.closure_type] || "bg-gray-100 text-gray-800"
              }`}
            >
              {o.closure_type.replace(/_/g, " ")}
            </span>

            <div className="grid grid-cols-2 gap-2 text-xs text-muted-foreground mt-2">
              <div>
                <span className="font-medium text-foreground">Crew:</span> {o.crew_size} people
              </div>
              <div>
                <span className="font-medium text-foreground">Vehicle:</span>{" "}
                {o.vehicle_name || "None"}
              </div>
              <div>
                <span className="font-medium text-foreground">Start:</span>{" "}
                {new Date(o.start_time).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
              </div>
              <div>
                <span className="font-medium text-foreground">End:</span>{" "}
                {new Date(o.end_time).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
              </div>
            </div>

            {o.location && (
              <div className="mt-2 text-xs text-muted-foreground truncate">
                {o.location}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
