"use client";

import { CircleNotch, WarningCircle } from "@phosphor-icons/react";
import type { HTMLAttributes, ReactNode } from "react";

import { cn } from "@/lib/cn";

export function Panel({
  children,
  className,
  ...props
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <section className={cn("panel", className)} {...props}>
      {children}
    </section>
  );
}

export function StatusBadge({
  children,
  status,
}: {
  children: ReactNode;
  status: string;
}) {
  const normalized = status.toLowerCase();
  return (
    <span
      className={cn(
        "status-badge",
        (normalized.includes("allow") ||
          normalized.includes("ground") ||
          normalized.includes("complete") ||
          normalized.includes("pass") ||
          normalized.includes("approve") ||
          normalized.includes("healthy")) &&
          "status-good",
        (normalized.includes("approval") ||
          normalized.includes("pending") ||
          normalized.includes("medium") ||
          normalized.includes("await")) &&
          "status-warn",
        (normalized.includes("block") ||
          normalized.includes("fail") ||
          normalized.includes("high") ||
          normalized.includes("error")) &&
          "status-bad",
        (normalized.includes("info") ||
          normalized.includes("queued") ||
          normalized.includes("running")) &&
          "status-info",
      )}
    >
      {children}
    </span>
  );
}

export function PageHeader({
  title,
  description,
  actions,
}: {
  title: string;
  description?: string;
  actions?: ReactNode;
}) {
  return (
    <header className="page-header">
      <div>
        <h1>{title}</h1>
        {description ? <p>{description}</p> : null}
      </div>
      {actions ? <div className="page-actions">{actions}</div> : null}
    </header>
  );
}

export function EmptyState({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <Panel className="empty-state">
      <WarningCircle size={28} />
      <h2>{title}</h2>
      <p>{description}</p>
    </Panel>
  );
}

export function LoadingState({ label = "Loading" }: { label?: string }) {
  return (
    <div className="loading-state" role="status">
      <CircleNotch className="spin" size={20} />
      {label}
    </div>
  );
}

export function MetricCard({
  label,
  value,
  detail,
  children,
}: {
  label: string;
  value: string;
  detail: string;
  children?: ReactNode;
}) {
  return (
    <Panel className="metric-card">
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{detail}</small>
      {children}
    </Panel>
  );
}
