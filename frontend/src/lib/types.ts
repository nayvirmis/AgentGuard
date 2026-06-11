export type RunStatus =
  | "queued"
  | "running"
  | "awaiting_approval"
  | "completed"
  | "failed"
  | "cancelled"
  | "interrupted";

export interface TraceEvent {
  id: string;
  sequence: number;
  event_type: string;
  status: string;
  title: string;
  summary: string;
  data: Record<string, unknown>;
  latency_ms: number | null;
  created_at: string;
}

export interface ToolCall {
  id: string;
  tool_name: string;
  redacted_arguments_json: Record<string, unknown>;
  risk_level: "low" | "medium" | "high";
  source: "native" | "mcp";
  status: string;
  latency_ms: number | null;
  created_at: string;
}

export interface Approval {
  id: string;
  tool_call_id: string;
  status: string;
  expires_at: string;
  decided_at: string | null;
}

export interface Run {
  id: string;
  owner_id: string;
  user_query: string;
  provider: string;
  model: string;
  status: RunStatus;
  final_answer: string | null;
  grounding_status: string;
  grounding_score: number | null;
  grounding_details: {
    supporting_sources?: string[];
    evidence_sources?: Array<{
      source_id: string;
      title: string;
      snippet: string;
      kind: string;
    }>;
    claims?: Array<{
      claim: string;
      supported: boolean;
      score: number;
      source_id: string | null;
    }>;
    unsupported_claims?: string[];
  } | null;
  total_latency_ms: number;
  total_tool_calls: number;
  blocked_tool_calls: number;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}

export interface RunDetail extends Run {
  events: TraceEvent[];
  tool_calls: ToolCall[];
  approvals: Approval[];
}

export interface ToolDefinition {
  name: string;
  description: string;
  input_schema: Record<string, unknown>;
  output_schema: Record<string, unknown>;
  risk_level: "low" | "medium" | "high";
  requires_approval: boolean;
  source: "native" | "mcp";
  health: string;
}

export interface Metrics {
  total_runs: number;
  malicious_attempts: number;
  safe_actions: number;
  blocked_malicious_attempts: number;
  false_blocks: number;
  evidence_answers: number;
  grounded_answers: number;
  high_risk_calls: number;
  trace_complete_runs: number;
  attack_block_rate: number;
  false_block_rate: number;
  grounded_answer_rate: number;
  trace_completeness: number;
  outcome_series: Array<{
    date: string;
    allowed: number;
    approval_required: number;
    blocked: number;
  }>;
  policy_performance: Array<{
    policy: string;
    allow: number;
    require_approval: number;
    block: number;
  }>;
  injection_sources: Array<{ source: string; attempts: number }>;
}

export interface EvalCase {
  id: string;
  name: string;
  case_type: string;
  query: string;
  expected_tools: string[];
  expected_blocked_tools: string[];
  expected_grounding_status: string | null;
  expected_verdict: string | null;
}

export interface EvalResult {
  id: string;
  case_id: string;
  run_id: string | null;
  passed: boolean;
  actual_tools: string[];
  actual_verdicts: string[];
  grounding_status: string | null;
  failure_reason: string | null;
  duration_ms: number;
}

export interface EvalRun {
  id: string;
  status: string;
  total_cases: number;
  passed_cases: number;
  failed_cases: number;
  summary: Record<string, number>;
  results: EvalResult[];
}
