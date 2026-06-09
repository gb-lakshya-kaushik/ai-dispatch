"use client";

import { DispatchProvider } from "./lib/dispatch-context";

export function Providers({ children }: { children: React.ReactNode }) {
  return <DispatchProvider>{children}</DispatchProvider>;
}
