"use client";

import {
  CalendarBlank,
  CaretDown,
  CaretRight,
  CheckCircle,
  Clock,
  Copy,
  Envelope,
  FileText,
  Warning,
  Wrench,
} from "@phosphor-icons/react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { API_URL, api } from "@/lib/api";
import type { TraceEvent } from "@/lib/types";

import { EmptyState, LoadingState, Panel, StatusBadge } from "./ui";

const toolIcons = {
  calendar_search: CalendarBlank,
  document_search: FileText,
  email_draft: Envelope,
  email_send_mock: Envelope,
};

function formatTime(value: string) {
  return new Intl.DateTimeFormat("en", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(new Date(value));
}

function policyState(event: TraceEvent | undefined, rule: string) {
  if (!event) return "not_triggered";
  const rules = (event.data.triggered_rules as string[] | undefined) ?? [];
  if (!rules.includes(rule)) return "not_triggered";
  return event.status;
}

export function RunDetailView({ runId }: { runId: string }) {
  const searchParams = useSearchParams();
  const initialView = searchParams.get("view") === "trace" ? "trace" : "execution";
  const [view, setView] = useState<"execution" | "trace">(initialView);
  const [selectedEvent, setSelectedEvent] = useState<number | null>(null);
  const queryClient = useQueryClient();
  const runQuery = useQuery({
    queryKey: ["run", runId],
    queryFn: () => api.getRun(runId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status && ["completed", "failed", "cancelled"].includes(status)
        ? false
        : 700;
    },
  });

  useEffect(() => {
    if (typeof EventSource === "undefined") return;
    const source = new EventSource(`${API_URL}/runs/${runId}/events`);
    const refresh = () => {
      void queryClient.invalidateQueries({ queryKey: ["run", runId] });
    };
    source.addEventListener("trace", refresh);
    source.addEventListener("end", () => {
      refresh();
      source.close();
    });
    source.onerror = () => source.close();
    return () => source.close();
  }, [queryClient, runId]);

  const decision = useMutation({
    mutationFn: ({
      approvalId,
      value,
    }: {
      approvalId: string;
      value: "approve" | "reject";
    }) => api.decideApproval(runId, approvalId, value),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["run", runId] }),
  });

  const run = runQuery.data;
  const currentEvent =
    run?.events.find((event) => event.sequence === selectedEvent) ??
    run?.events.find((event) => event.event_type === "policy_decision");
  if (runQuery.isLoading) return <LoadingState label="Loading execution trace" />;
  if (!run) {
    return (
      <div className="page">
        <EmptyState title="Run not found" description="This trace is unavailable." />
      </div>
    );
  }

  const pendingApproval = run.approvals.find((approval) => approval.status === "pending");
  const lastPolicy = [...run.events]
    .reverse()
    .find((event) => event.event_type === "policy_decision");

  return (
    <div className="page-with-inspector">
      <div className="page-primary">
        <div className="run-titlebar">
          <div>
            <div className="run-view-switch">
              <button
                className={view === "execution" ? "view-active" : ""}
                onClick={() => setView("execution")}
              >
                Execution
              </button>
              <button
                className={view === "trace" ? "view-active" : ""}
                onClick={() => setView("trace")}
              >
                Trace Explorer
              </button>
            </div>
            <div className="run-id-row">
              <h1 className="mono">{run.id}</h1>
              <button
                className="icon-button"
                aria-label="Copy run ID"
                onClick={() => navigator.clipboard.writeText(run.id)}
              >
                <Copy size={18} />
              </button>
              <StatusBadge status={run.status}>{run.status.replaceAll("_", " ")}</StatusBadge>
            </div>
            <div className="run-meta mono">
              <span>
                <Clock size={16} /> {(run.total_latency_ms / 1000).toFixed(2)}s
              </span>
              <span>{run.total_tool_calls} tool calls</span>
              <span>{run.approvals.length} approvals</span>
              <span>{Math.round((run.grounding_score ?? 0) * 100)}% grounding</span>
            </div>
          </div>
        </div>

        {view === "execution" ? (
          <ExecutionView
            run={run}
            deciding={decision.isPending}
            decide={(value) =>
              pendingApproval &&
              decision.mutate({ approvalId: pendingApproval.id, value })
            }
          />
        ) : (
          <TraceView
            events={run.events}
            selected={currentEvent?.sequence ?? null}
            onSelect={setSelectedEvent}
          />
        )}
      </div>
      <aside className="inspector">
        {view === "execution" ? (
          <ExecutionInspector run={run} policyEvent={lastPolicy} />
        ) : (
          <EventInspector event={currentEvent} />
        )}
      </aside>
    </div>
  );
}

function ExecutionView({
  run,
  deciding,
  decide,
}: {
  run: Awaited<ReturnType<typeof api.getRun>>;
  deciding: boolean;
  decide: (value: "approve" | "reject") => void;
}) {
  return (
    <>
      <Panel className="task-panel">
        <span className="eyebrow">Task</span>
        <p className="mono">{run.user_query}</p>
      </Panel>
      <section className="execution-section">
        <h2>Execution Flow</h2>
        <div className="execution-flow">
          {run.tool_calls.map((call, index) => {
            const Icon = toolIcons[call.tool_name as keyof typeof toolIcons] ?? Wrench;
            const approval = run.approvals.find((item) => item.tool_call_id === call.id);
            const status =
              approval?.status === "pending"
                ? "requires approval"
                : call.status === "executed"
                  ? "allowed"
                  : call.status;
            const expanded = approval?.status === "pending";
            return (
              <div className="flow-step" key={call.id}>
                <div className={`step-number step-${status.replaceAll(" ", "-")}`}>
                  {index + 1}
                </div>
                <Panel className={expanded ? "flow-card flow-card-approval" : "flow-card"}>
                  <div className="flow-row">
                    <span className="flow-name mono">
                      <Icon size={19} />
                      {call.tool_name}
                    </span>
                    <StatusBadge status={status}>{status.replaceAll("_", " ")}</StatusBadge>
                    <span className="mono muted">
                      {call.latency_ms ? `${(call.latency_ms / 1000).toFixed(2)}s` : "—"}
                    </span>
                    {expanded ? <CaretDown /> : <CaretRight />}
                  </div>
                  {expanded ? (
                    <div className="approval-panel">
                      <div className="approval-copy">
                        <Warning size={30} />
                        <p>
                          This action simulates sending an email to an external
                          recipient. Approval is required before the agent proceeds.
                        </p>
                      </div>
                      <dl>
                        <dt>Destination type</dt>
                        <dd>External recipient (professor@example.edu)</dd>
                        <dt>Risk class</dt>
                        <dd>High — External communication</dd>
                      </dl>
                      <div className="approval-actions">
                        <button
                          className="button"
                          disabled={deciding}
                          onClick={() => decide("reject")}
                        >
                          Reject
                        </button>
                        <button
                          className="button button-approve"
                          disabled={deciding}
                          onClick={() => decide("approve")}
                        >
                          Approve
                        </button>
                      </div>
                    </div>
                  ) : null}
                </Panel>
              </div>
            );
          })}
          {!run.tool_calls.length ? (
            <Panel className="empty-flow">Provider planning is in progress.</Panel>
          ) : null}
        </div>
      </section>

      <section>
        <h2>Evidence &amp; Citations</h2>
        <Panel className="evidence-panel">
          <div className="evidence-header">
            <span>Source ID</span>
            <span>Source</span>
            <span>Snippet</span>
            <span>Confidence</span>
          </div>
          {run.grounding_details?.supporting_sources?.length ? (
            run.grounding_details.evidence_sources
              ?.filter((source) =>
                run.grounding_details?.supporting_sources?.includes(source.source_id),
              )
              .map((source) => (
                <div className="evidence-row" key={source.source_id}>
                  <strong className="mono">{source.source_id}</strong>
                  <span>{source.title}</span>
                  <span>{source.snippet}</span>
                  <StatusBadge status="grounded">
                    {Math.round((run.grounding_score ?? 0) * 100)}%
                  </StatusBadge>
                </div>
              ))
          ) : (
            <div className="evidence-empty">
              Evidence will appear after document search and grounding.
            </div>
          )}
        </Panel>
      </section>
      {run.final_answer ? (
        <Panel className="final-answer">
          <span className="eyebrow">Final answer</span>
          <p>{run.final_answer}</p>
        </Panel>
      ) : null}
    </>
  );
}

function TraceView({
  events,
  selected,
  onSelect,
}: {
  events: TraceEvent[];
  selected: number | null;
  onSelect: (value: number) => void;
}) {
  const [query, setQuery] = useState("");
  const visible = events.filter((event) =>
    `${event.event_type} ${event.title} ${event.summary}`
      .toLowerCase()
      .includes(query.toLowerCase()),
  );
  return (
    <>
      <div className="toolbar trace-toolbar">
        <input
          className="input"
          placeholder="Search events, tool names, rule IDs, hashes"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
        <select className="select"><option>All event types</option></select>
        <select className="select"><option>All statuses</option></select>
        <button className="button">Export</button>
      </div>
      <Panel className="trace-table">
        <div className="trace-head">
          <span>Timestamp</span><span>Event</span><span>Details</span><span>Duration</span><span>Status</span>
        </div>
        {visible.map((event) => (
          <button
            className={`trace-row ${selected === event.sequence ? "row-selected" : ""}`}
            key={event.id}
            onClick={() => onSelect(event.sequence)}
          >
            <span className="trace-index">{event.sequence}</span>
            <span className="mono">{formatTime(event.created_at)}</span>
            <strong className="mono">{event.event_type}</strong>
            <span>{event.summary}</span>
            <span className="mono">{event.latency_ms ? `${event.latency_ms}ms` : "—"}</span>
            <StatusBadge status={event.status}>{event.status.replaceAll("_", " ")}</StatusBadge>
          </button>
        ))}
      </Panel>
    </>
  );
}

function ExecutionInspector({
  run,
  policyEvent,
}: {
  run: Awaited<ReturnType<typeof api.getRun>>;
  policyEvent: TraceEvent | undefined;
}) {
  const policies = [
    "POLICY_HIGH_RISK_APPROVAL",
    "POLICY_PROMPT_INJECTION",
    "POLICY_SENSITIVE_DATA",
  ];
  const score = Math.round((run.grounding_score ?? 0) * 100);
  return (
    <>
      <h2>Policy Rules</h2>
      <div className="inspector-section policy-list">
        {policies.map((policy) => {
          const state = policyState(policyEvent, policy);
          return (
            <div className="policy-row" key={policy}>
              <span className="mono">{policy}</span>
              <StatusBadge status={state}>{state.replaceAll("_", " ")}</StatusBadge>
            </div>
          );
        })}
      </div>
      <div className="inspector-section">
        <h3>Grounding confidence: {score}%</h3>
        <div className="progress"><span style={{ width: `${score}%` }} /></div>
      </div>
      <div className="inspector-section">
        <h3>Evidence checklist</h3>
        <div className="check-list">
          {[
            "Calendar data retrieved",
            "Academic handbook referenced",
            "Extension policy verified",
            "Email draft grounded in source",
          ].map((label) => (
            <div className="check-row" key={label}>
              <span>{label}</span>
              <CheckCircle size={18} color="var(--teal)" weight="fill" />
            </div>
          ))}
        </div>
      </div>
      <div className="inspector-section">
        <h3>Status legend</h3>
        <div className="legend-list">
          {[
            ["Allowed", "Action permitted"],
            ["Requires approval", "Human approval required"],
            ["Blocked", "Action blocked by policy"],
            ["Grounded", "Supported by evidence"],
          ].map(([status, detail]) => (
            <div className="legend-row" key={status}>
              <StatusBadge status={status}>{status}</StatusBadge>
              <span className="muted">{detail}</span>
            </div>
          ))}
        </div>
      </div>
    </>
  );
}

function EventInspector({ event }: { event: TraceEvent | undefined }) {
  if (!event) return <p className="muted">Select an event to inspect it.</p>;
  return (
    <>
      <h2>Event Inspector</h2>
      <div className="inspector-section event-metadata">
        <dl>
          <dt>Event</dt><dd className="mono">{event.event_type}</dd>
          <dt>Timestamp</dt><dd className="mono">{formatTime(event.created_at)}</dd>
          <dt>Duration</dt><dd className="mono">{event.latency_ms ?? 0}ms</dd>
          <dt>Status</dt><dd><StatusBadge status={event.status}>{event.status}</StatusBadge></dd>
        </dl>
      </div>
      <div className="inspector-section">
        <h3>Sanitized event data</h3>
        <pre className="code-block">{JSON.stringify(event.data, null, 2)}</pre>
      </div>
      <div className="inspector-section">
        <h3>Summary</h3>
        <p>{event.summary}</p>
      </div>
    </>
  );
}
