import { ApiError } from "./types";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const BASE = "/api/policies";
const TIMEOUT_MS = 30_000;

// ---------------------------------------------------------------------------
// Enums / Type Aliases
// ---------------------------------------------------------------------------

export type PolicyDomain = "attendance" | "leave" | "overtime" | "disciplinary";

export type RuleOperator =
  | "equals"
  | "not_equals"
  | "greater_than"
  | "less_than"
  | "greater_than_or_equal"
  | "less_than_or_equal"
  | "in_list"
  | "not_in_list"
  | "between"
  | "is_null";

export type ActionType =
  | "flag"
  | "notify"
  | "calculate"
  | "restrict"
  | "escalate";

// ---------------------------------------------------------------------------
// Shared / Nested Types
// ---------------------------------------------------------------------------

export interface RuleCondition {
  field: string;
  operator: RuleOperator;
  value: unknown;
}

export interface RuleAction {
  type: ActionType;
  parameters: Record<string, unknown>;
}

// ---------------------------------------------------------------------------
// Policy Rule Types
// ---------------------------------------------------------------------------

export interface PolicyRule {
  id: string;
  tenant_id: string;
  domain: PolicyDomain;
  rule_id: string;
  name: string;
  description: string;
  rule_condition: RuleCondition;
  rule_action: RuleAction;
  priority: number;
  enabled: boolean;
  template_rule_id: string | null;
  is_custom: boolean;
  is_deleted: boolean;
  created_at: string;
  updated_at: string;
  created_by: string;
}

export interface PolicyRulesGrouped {
  attendance: PolicyRule[];
  leave: PolicyRule[];
  overtime: PolicyRule[];
  disciplinary: PolicyRule[];
}

export interface PolicyRuleCreateRequest {
  domain: PolicyDomain;
  rule_id: string;
  name: string;
  description: string;
  rule_condition: RuleCondition;
  rule_action: RuleAction;
  priority: number;
  enabled?: boolean;
}

export interface PolicyRuleUpdateRequest {
  name?: string;
  description?: string;
  rule_condition?: RuleCondition;
  rule_action?: RuleAction;
  priority?: number;
  enabled?: boolean;
}

// ---------------------------------------------------------------------------
// Policy Evaluation Types
// ---------------------------------------------------------------------------

export interface PolicyEvaluateRequest {
  tenant_id: string;
  domain: PolicyDomain;
  event_type: string;
  context: Record<string, unknown>;
  evaluation_date?: string; // YYYY-MM-DD
}

export interface MatchedRule {
  rule_id: string;
  name: string;
  priority: number;
}

export interface EvaluationResult {
  rule_id: string;
  passed: boolean;
  condition: Record<string, unknown>;
}

export interface TriggeredAction {
  rule_id: string;
  action_type: ActionType;
  parameters: Record<string, unknown>;
}

export interface PolicyEvaluateResponse {
  matched_rules: MatchedRule[];
  evaluation_results: EvaluationResult[];
  triggered_actions: TriggeredAction[];
}

// ---------------------------------------------------------------------------
// Policy Version Types
// ---------------------------------------------------------------------------

export interface PolicyVersion {
  id: string;
  tenant_id: string;
  version_number: number;
  change_summary: string;
  rules_added: number;
  rules_removed: number;
  rules_modified: number;
  effective_date: string; // YYYY-MM-DD
  published_by: string;
  published_at: string;
}

export interface PolicyVersionListResponse {
  items: PolicyVersion[];
  total: number;
  page: number;
  page_size: number;
}

// ---------------------------------------------------------------------------
// Policy Diff Types
// ---------------------------------------------------------------------------

export interface RuleDiffEntry {
  rule_id: string;
  name: string;
  details: Record<string, unknown> | null;
}

export interface PolicyDiffResponse {
  version_a: number;
  version_b: number;
  rules_added: RuleDiffEntry[];
  rules_removed: RuleDiffEntry[];
  rules_modified: RuleDiffEntry[];
  rules_unchanged: RuleDiffEntry[];
}

// ---------------------------------------------------------------------------
// Publish Types
// ---------------------------------------------------------------------------

export interface PublishRequest {
  effective_date?: string; // YYYY-MM-DD
  change_summary: string;
}

// ---------------------------------------------------------------------------
// Internal Helpers
// ---------------------------------------------------------------------------

async function fetchWithTimeout(
  url: string,
  options: RequestInit = {},
): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), TIMEOUT_MS);
  try {
    return await fetch(url, {
      ...options,
      credentials: "include",
      signal: controller.signal,
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new ApiError(0, "TIMEOUT", "Yêu cầu đã hết thời gian chờ");
    }
    throw new ApiError(0, "NETWORK_ERROR", "Lỗi kết nối mạng");
  } finally {
    clearTimeout(timeoutId);
  }
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (res.status === 401) {
    window.location.href = "/login";
    return new Promise(() => {}); // never resolves
  }
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    const message =
      body?.detail?.message ||
      body?.detail ||
      body?.error?.message ||
      `Yêu cầu thất bại: ${res.status}`;
    const errorCode =
      body?.detail?.code ||
      body?.error_code ||
      body?.error?.code ||
      "UNKNOWN_ERROR";
    throw new ApiError(res.status, errorCode, message, body);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

// ---------------------------------------------------------------------------
// Policy Rules API
// ---------------------------------------------------------------------------

/**
 * List all policy rules for the authenticated tenant, grouped by domain.
 */
export async function listRules(): Promise<PolicyRulesGrouped> {
  const res = await fetchWithTimeout(`${BASE}/rules`);
  return handleResponse<PolicyRulesGrouped>(res);
}

/**
 * Create a new custom policy rule.
 */
export async function createRule(
  data: PolicyRuleCreateRequest,
): Promise<PolicyRule> {
  const res = await fetchWithTimeout(`${BASE}/rules`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return handleResponse<PolicyRule>(res);
}

/**
 * Update an existing policy rule or create an override for a template rule.
 */
export async function updateRule(
  ruleId: string,
  data: PolicyRuleUpdateRequest,
): Promise<PolicyRule> {
  const res = await fetchWithTimeout(
    `${BASE}/rules/${encodeURIComponent(ruleId)}`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    },
  );
  return handleResponse<PolicyRule>(res);
}

/**
 * Soft-delete a custom policy rule (or disable a template rule).
 */
export async function deleteRule(ruleId: string): Promise<void> {
  const res = await fetchWithTimeout(
    `${BASE}/rules/${encodeURIComponent(ruleId)}`,
    {
      method: "DELETE",
    },
  );
  await handleResponse<void>(res);
}

// ---------------------------------------------------------------------------
// Policy Publish API
// ---------------------------------------------------------------------------

/**
 * Publish current draft state as a new policy version.
 */
export async function publishPolicy(
  data: PublishRequest,
): Promise<PolicyVersion> {
  const res = await fetchWithTimeout(`${BASE}/publish`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return handleResponse<PolicyVersion>(res);
}

// ---------------------------------------------------------------------------
// Policy Versions API
// ---------------------------------------------------------------------------

/**
 * Get paginated version history for the authenticated tenant.
 */
export async function listVersions(params?: {
  page?: number;
  page_size?: number;
}): Promise<PolicyVersionListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.page) searchParams.set("page", String(params.page));
  if (params?.page_size)
    searchParams.set("page_size", String(params.page_size));

  const query = searchParams.toString();
  const url = `${BASE}/versions${query ? `?${query}` : ""}`;
  const res = await fetchWithTimeout(url);
  return handleResponse<PolicyVersionListResponse>(res);
}

/**
 * Get diff between two policy versions.
 */
export async function getVersionDiff(
  versionNumber: number,
  otherVersion: number,
): Promise<PolicyDiffResponse> {
  const res = await fetchWithTimeout(
    `${BASE}/versions/${versionNumber}/diff/${otherVersion}`,
  );
  return handleResponse<PolicyDiffResponse>(res);
}

/**
 * Rollback to a previous policy version (creates a new version with the target's snapshot).
 */
export async function rollbackVersion(
  versionNumber: number,
): Promise<PolicyVersion> {
  const res = await fetchWithTimeout(
    `${BASE}/versions/${versionNumber}/rollback`,
    { method: "POST" },
  );
  return handleResponse<PolicyVersion>(res);
}

// ---------------------------------------------------------------------------
// Policy Evaluation API
// ---------------------------------------------------------------------------

/**
 * Evaluate policy rules against a given context.
 */
export async function evaluatePolicy(
  data: PolicyEvaluateRequest,
): Promise<PolicyEvaluateResponse> {
  const res = await fetchWithTimeout(`${BASE}/evaluate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return handleResponse<PolicyEvaluateResponse>(res);
}
