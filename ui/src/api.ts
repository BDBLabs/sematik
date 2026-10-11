// src/api.ts — lightweight fetch wrapper for the sematik API
const BASE = import.meta.env.DEV ? "http://localhost:8000" : "";

export async function api<T>(path: string, body?: unknown): Promise<T> {
  const opts: RequestInit = {
    headers: { "Content-Type": "application/json" },
  };
  if (body !== undefined) opts.method = "POST"; opts.body = JSON.stringify(body);
  if (!opts.method && !opts.body) opts.method = "GET";
  const r = await fetch(`${BASE}${path}`, opts);
  if (!r.ok) {
    const txt = await r.text();
    throw new Error(`API ${r.status}: ${txt}`);
  }
  return r.json() as Promise<T>;
}

export interface Row { [k: string]: unknown }
export interface MappingIn {
  source_artifact: string;
  canonical_concept: string;
  target_artifact?: string;
  confidence?: { overall: number; drivers?: string[]; calibrated?: boolean };
  levels?: LevelIn[];
  approved_by?: string;
  approval_ref?: string;
  version?: string;
  evidence_refs?: string[];
  golden_plan_digest?: string;
  rule_refs?: string[];
  domain_pack?: string;
  id?: string | null;
}
export interface LevelIn { level: number; kind: string; statement: string; context?: Record<string, unknown> }
export interface StepIn { op: string; args: Record<string, unknown> }

export const health = () => api<{status: string}>("/api/v1/health");
export const loadFixture = (name: string) =>
  api<unknown>(`/api/v1/fixture/${name}`);
export const profileColumn = (name: string, values: unknown[]) =>
  api<Record<string, unknown>>("/api/v1/profile", { name, values });
export const getHypotheses = (name: string, values: unknown[]) =>
  api<any[]>("/api/v1/hypotheses", { name, values });
export const getCandidates = (tables: Record<string, Row[]>) =>
  api<any[]>("/api/v1/candidates", { tables });
export const mappingDigest = (m: MappingIn) =>
  api<Record<string, unknown>>("/api/v1/mapping/digest", m);
export const compilePlan = (m: MappingIn, steps: StepIn[]) =>
  api<Record<string, unknown>>("/api/v1/compile", { mapping: m, steps });
export const compileSql = (m: MappingIn, steps: StepIn[], sourceTable: string, dialect = "postgres") =>
  api<Record<string, unknown>>("/api/v1/compile-sql", { mapping: m, steps, source_table: sourceTable, dialect });
export const executePlan = (payload: { mapping: MappingIn; steps: StepIn[]; rows: Row[]; require_golden?: boolean; golden?: any[] }) =>
  api<Record<string, unknown>>("/api/v1/execute", payload);
export const popRecon = (rows: Row[], outputs: Row[], sk: string, tk: string) =>
  api<Record<string, unknown>>("/api/v1/reconcile/population", { rows, outputs, source_key: sk, target_key: tk });
export const conceptEntropy = (hyps: any[]) =>
  api<{ entropy: number } | { detail: string }>("/api/v1/entropy/concept", hyps);
export const semanticEntropy = (hyps: any[]) =>
  api<{ entropy: number } | { detail: string }>("/api/v1/entropy/semantic", hyps);
export const semanticEntropyFlagged = (hyps: any[]) =>
  api<{ entropy: number; warnings: string[] }>("/api/v1/entropy/semantic-flagged", hyps);
