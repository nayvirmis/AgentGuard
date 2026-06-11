"use client";

import {
  ChartBar,
  Flask,
  List,
  Play,
  ShieldCheck,
  TerminalWindow,
  Toolbox,
  X,
} from "@phosphor-icons/react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { type ReactNode, useState } from "react";

import { cn } from "@/lib/cn";

const navigation = [
  { href: "/playground", label: "Playground", icon: Play },
  { href: "/runs", label: "Runs", icon: TerminalWindow },
  { href: "/security", label: "Security", icon: ShieldCheck },
  { href: "/evaluations", label: "Evaluations", icon: ChartBar },
  { href: "/tools", label: "Tools", icon: Toolbox },
  { href: "/policies", label: "Policies", icon: Flask },
];

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  return (
    <div className="app-shell">
      <div className="mobile-topbar">
        <Link href="/playground" className="mobile-brand">
          <ShieldCheck size={25} weight="duotone" />
          <span>AgentGuard</span>
        </Link>
      </div>
      <button
        className="mobile-menu"
        onClick={() => setOpen((value) => !value)}
        aria-label={open ? "Close navigation" : "Open navigation"}
      >
        {open ? <X size={22} /> : <List size={22} />}
      </button>
      <aside className={cn("sidebar", open && "sidebar-open")}>
        <Link href="/playground" className="brand" onClick={() => setOpen(false)}>
          <span className="brand-mark">
            <ShieldCheck size={25} weight="duotone" />
          </span>
          <span>AgentGuard</span>
        </Link>
        <nav aria-label="Primary navigation">
          {navigation.map((item) => {
            const active =
              pathname === item.href ||
              (item.href === "/runs" && pathname.startsWith("/runs/"));
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn("nav-item", active && "nav-item-active")}
                onClick={() => setOpen(false)}
              >
                <Icon size={20} />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>
        <div className="sidebar-spacer" />
        <div className="workspace-block">
          <span className="eyebrow">Workspace</span>
          <button className="workspace-select">Acme University</button>
          <span className="eyebrow">Environment</span>
          <button className="workspace-select">Production</button>
        </div>
        <div className="profile">
          <span className="avatar">AD</span>
          <span>
            <strong>Alex Developer</strong>
            <small>alex.dev@acme.edu</small>
          </span>
        </div>
      </aside>
      {open ? (
        <button className="sidebar-backdrop" onClick={() => setOpen(false)} aria-label="Close menu" />
      ) : null}
      <main className="main-content">{children}</main>
    </div>
  );
}
