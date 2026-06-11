import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { MetricCard, PageHeader, StatusBadge } from "./ui";

describe("workbench UI primitives", () => {
  it("maps policy states to accessible visible badges", () => {
    render(<StatusBadge status="require_approval">Requires approval</StatusBadge>);
    const badge = screen.getByText("Requires approval");
    expect(badge).toHaveClass("status-warn");
  });

  it("renders page context and dashboard metrics", () => {
    render(
      <>
        <PageHeader title="Security Dashboard" description="Policy metrics" />
        <MetricCard label="Trace completeness" value="100%" detail="24 runs" />
      </>,
    );
    expect(screen.getByRole("heading", { name: "Security Dashboard" })).toBeInTheDocument();
    expect(screen.getByText("Trace completeness")).toBeInTheDocument();
    expect(screen.getByText("100%")).toBeInTheDocument();
  });
});
