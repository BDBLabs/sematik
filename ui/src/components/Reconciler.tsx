// src/components/Reconciler.tsx
import React, { useState } from "react";
import { popRecon, recRecon } from "../api";
import type { Row } from "../api";

interface Props {
  rows: Row[];
  execResult: any;
}

interface Mismatch {
  key: string;
  field: string;
  kind: string;
  reason: string;
}

export default function Reconciler({ rows, execResult }: Props) {
  const [loading, setLoading] = useState(false);
  const [loadingRec, setLoadingRec] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [recResult, setRecResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const runPop = async () => {
    if (!execResult?.outputs) return;
    setLoading(true); setError(null);
    try {
      const r = await popRecon(
        rows,
        execResult.outputs as Row[],
        "_id",
        "_id",
      );
      setResult(r);
    } catch (e: any) { setError(e.message); } finally { setLoading(false); }
  };

  const runRec = async () => {
    if (!execResult?.outputs) return;
    const numericFields = Object.keys(execResult.outputs[0] || {})
      .filter((k) => typeof execResult.outputs[0][k] === "number");
    const pairs = numericFields.map((f) => [f, f] as [string, string]);
    if (pairs.length === 0) {
      alert("No numeric fields found in output for record-level comparison.");
      return;
    }
    setLoadingRec(true); setError(null);
    try {
      const r = await recRecon(
        rows,
        execResult.outputs as Row[],
        "_id",
        "_id",
        pairs,
      );
      setRecResult(r);
    } catch (e: any) { setError(e.message); } finally { setLoadingRec(false); }
  };

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">Reconciler (§30)</h2>
      <p className="text-sm text-slate-400">
        Compare input rows against converted output. Population reconciliation
        checks aggregate counts; record-level reconciliation verifies each row's
        values individually and catches misattached values.
      </p>

      <div className="flex gap-2">
        <button onClick={runPop}
          disabled={loading || rows.length === 0 || !execResult?.outputs}
          className="px-4 py-2 bg-blue-600 rounded hover:bg-blue-700 disabled:opacity-50">
          {loading ? "Reconciling…" : "Run Population Reconciliation"}
        </button>
        <button onClick={runRec}
          disabled={loadingRec || rows.length === 0 || !execResult?.outputs}
          className="px-4 py-2 bg-cyan-600 rounded hover:bg-cyan-700 disabled:opacity-50">
          {loadingRec ? "Reconciling…" : "Run Record-Level Reconciliation"}
        </button>
      </div>

      {!execResult && (
        <p className="text-sm text-slate-400">Run a conversion first in the Executor tab.</p>
      )}

      {error && (
        <pre className="bg-red-900/30 border border-red-700 rounded p-3 text-sm text-red-300">
          {error}
        </pre>
      )}

      {/* Population reconciliation results */}
      {result && (
        <div className="space-y-3">
          <h3 className="font-medium">Population Reconciliation</h3>
          <div className="grid grid-cols-3 gap-4 text-center">
            <div><span className="text-2xl font-bold text-blue-400">{result.source_records}</span><div className="text-xs text-slate-400">Input</div></div>
            <div><span className="text-2xl font-bold text-cyan-400">{result.target_records}</span><div className="text-xs text-slate-400">Output</div></div>
            <div><span className={`text-2xl font-bold ${result.balanced ? "text-green-400" : "text-amber-400"}`}>{result.balanced ? "Balanced" : "Mismatch"}</span><div className="text-xs text-slate-400">Status</div></div>
          </div>
          {(result.missing_in_target?.length > 0 || result.extra_in_target?.length > 0) && (
            <div className="text-sm">
              {result.missing_in_target?.length > 0 && (
                <span className="text-amber-400">Missing in output: {result.missing_in_target.join(", ")} </span>
              )}
              {result.extra_in_target?.length > 0 && (
                <span className="text-amber-400">Extra in output: {result.extra_in_target.join(", ")}</span>
              )}
            </div>
          )}
        </div>
      )}

      {/* Record-level reconciliation results */}
      {recResult && (
        <div className="space-y-3">
          <h3 className="font-medium">Record-Level Reconciliation (§30)</h3>
          <div className="grid grid-cols-4 gap-4 text-center">
            <div><span className="text-2xl font-bold text-blue-400">{recResult.checked}</span><div className="text-xs text-slate-400">Checked</div></div>
            <div><span className="text-2xl font-bold text-cyan-400">{(recResult.mismatches || []).length}</span><div className="text-xs text-slate-400">Mismatches</div></div>
            <div><span className="text-2xl font-bold text-amber-400">{(recResult.unmatched || []).length}</span><div className="text-xs text-slate-400">Unmatched</div></div>
            <div><span className={`text-2xl font-bold ${recResult.balanced ? "text-green-400" : "text-amber-400"}`}>{recResult.balanced ? "Balanced" : "Issues"}</span><div className="text-xs text-slate-400">Status</div></div>
          </div>

          {(recResult.mismatches || []).length > 0 && (
            <div className="space-y-2">
              <h4 className="text-sm font-medium text-amber-400">Mismatches ({recResult.mismatches.length})</h4>
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-slate-700 text-xs text-slate-400">
                    <th className="pb-1">Record ID</th>
                    <th className="pb-1">Field</th>
                    <th className="pb-1">Kind</th>
                    <th className="pb-1">Reason</th>
                  </tr>
                </thead>
                <tbody>
                  {recResult.mismatches.map((m: Mismatch, i: number) => (
                    <tr key={i} className="border-b border-slate-800">
                      <td className="py-1">{m.key}</td>
                      <td className="py-1">{m.field}</td>
                      <td className="py-1">
                        <span className={`text-xs px-2 py-0.5 rounded ${
                          m.kind === "missing_target" ? "bg-red-900/30 text-red-400"
                          : m.kind === "invalid_target" ? "bg-orange-900/30 text-orange-400"
                          : "bg-amber-900/30 text-amber-400"
                        }`}>{m.kind}</span>
                      </td>
                      <td className="py-1 text-slate-400 text-xs">{m.reason}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {(recResult.unmatched || []).length > 0 && (
            <div className="space-y-1">
              <h4 className="text-sm font-medium text-amber-400">Unmatched output records</h4>
              <div className="flex flex-wrap gap-1 text-xs">
                {(recResult.unmatched as string[]).map((id, i) => (
                  <span key={i} className="bg-amber-900/30 text-amber-400 px-2 py-1 rounded">{id}</span>
                ))}
              </div>
            </div>
          )}

          {(recResult.duplicates || []).length > 0 && (
            <div className="space-y-1">
              <h4 className="text-sm font-medium text-red-400">Duplicate keys</h4>
              <div className="flex flex-wrap gap-1 text-xs">
                {(recResult.duplicates as string[]).map((id, i) => (
                  <span key={i} className="bg-red-900/30 text-red-400 px-2 py-1 rounded">{id}</span>
                ))}
              </div>
            </div>
          )}

          {recResult.balanced && (
            <div className="text-sm text-green-400 bg-green-900/20 border border-green-800 rounded p-2">
              ✅ All {recResult.checked} records verified — no mismatches, no unmatched, no duplicates.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
