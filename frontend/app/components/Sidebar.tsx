"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useDispatch } from "../lib/dispatch-context";

const nav = [
  { href: "/", label: "Dashboard", icon: "grid" },
  { href: "/personnel", label: "Personnel", icon: "users" },
  { href: "/service-orders", label: "Service Orders", icon: "clipboard" },
  { href: "/dispatch", label: "Dispatch Flow", icon: "play", children: [
    { href: "/dispatch", label: "Pipeline" },
    { href: "/dispatch/summary", label: "Summary" },
  ]},
  { href: "/copilot", label: "AI Copilot", icon: "message" },
];

const icons: Record<string, React.ReactNode> = {
  grid: <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" /></svg>,
  users: <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" /></svg>,
  clipboard: <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" /></svg>,
  play: <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>,
  message: <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" /></svg>,
};

export function Sidebar() {
  const pathname = usePathname();
  const { step, reset } = useDispatch();
  const hasResult = step === "done";

  return (
    <aside className="w-64 bg-sidebar-bg flex flex-col">
      <div className="p-5 border-b border-white/10">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-sidebar-active rounded-lg flex items-center justify-center">
            <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
          </div>
          <div>
            <h1 className="text-base font-bold text-sidebar-text">AI Dispatch</h1>
            <p className="text-[10px] text-sidebar-muted tracking-wide uppercase">Workforce Optimization</p>
          </div>
        </div>
      </div>
      <nav className="flex-1 px-3 py-4 space-y-1">
        {nav.map((item) => {
          const isDispatch = item.href === "/dispatch";
          const active = isDispatch
            ? pathname.startsWith("/dispatch")
            : pathname === item.href;

          return (
            <div key={item.href}>
              <Link
                href={item.href}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
                  active
                    ? "bg-sidebar-active text-white shadow-lg shadow-orange-500/20"
                    : "text-sidebar-muted hover:bg-sidebar-hover hover:text-sidebar-text"
                }`}
              >
                {icons[item.icon]}
                {item.label}
              </Link>
              {/* Sub-nav for dispatch */}
              {isDispatch && active && item.children && (
                <div className="ml-8 mt-1.5 space-y-0.5">
                  {item.children.map((child) => {
                    const childActive = pathname === child.href;
                    const disabled = child.href === "/dispatch/summary" && !hasResult;
                    return (
                      <Link
                        key={child.href}
                        href={disabled ? "#" : child.href}
                        className={`block px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                          childActive
                            ? "bg-white/10 text-white"
                            : disabled
                            ? "text-sidebar-muted/40 cursor-not-allowed"
                            : "text-sidebar-muted hover:text-sidebar-text hover:bg-white/5"
                        }`}
                        onClick={(e) => disabled && e.preventDefault()}
                      >
                        {child.label}
                      </Link>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </nav>

      {/* Start New button */}
      {hasResult && (
        <div className="px-3 pb-3">
          <button
            onClick={reset}
            className="w-full px-3 py-2.5 border border-white/10 rounded-lg text-xs font-medium text-sidebar-muted hover:bg-sidebar-hover hover:text-sidebar-text transition-colors"
          >
            Start New Dispatch
          </button>
        </div>
      )}

      <div className="px-5 py-4 border-t border-white/10 text-[10px] text-sidebar-muted">
        Traffic Management Inc. — v0.1
      </div>
    </aside>
  );
}
