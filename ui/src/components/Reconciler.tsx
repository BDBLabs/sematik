// src/components/Reconciler.tsx
import React, { useState } from "react";
import { popRecon } from "../api";
import type { Row } from "../api";

interface Props {
  rows: Row[];
  execResult: any;
}

export default function Reconciler({ rows, execResult }: Props) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const run = async () => {
    if (!execResult?.converted_rows) return;
    setLoading(true); setError(null);
    try {
      const r = await popRecon(
        rows,
        execResult.converted_rows as Row[],
        "_id",
        "_id",
      );
      setResult(r);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">Reconciler (§30)</h2>
      <p className="text-sm text-slate-400">
        Population reconciliation: compares input rows against converted output.
      </p>

      <button onClick={run}
        disabled={loading || rows.length === 0 || !execResult?.converted_rows}
        className="px-4 py-2 bg-blue-600 rounded hover:bg-blue-700 disabled:opacity-50">
        {loading ? "Reconciling…" : "Run Population Reconciliation"}
      </button>

      {!execResult && (
        <p className="text-sm text-slate-400">Run a conversion first in the Executor tab.</p>
      )}

      {error && (
        <pre className="bg-red-900/30 border border-red-700 rounded p-3 text-sm text-red-300">
          {error}
        </pre>
      )}

      {result && (
        <div className="space-y-3">
          <div className="grid grid-cols-3 gap-4 text-center">
            <div><span className="text-2xl font-bold text-blue-400">{result.input_population}</span><div className="text-xs text-slate-400">Input</div></div>
            <div><span className="text-2xl font-bold text-cyan-400">{result.output_population}</span><div className="text-xs text-slate-400">Output</div></div>
            <div><span className={`text-2xl font-bold ${result.delta === 0 ? "text-green-400" : "text-amber-400"}`}>{result.delta}</span><div className="text-xs text-slate-400">Delta</div></div>
          </div>
          {result.matched_pairs !== undefined && (
            <p className="text-sm text-slate-300">Matched pairs: {result.matched_pairs}</p>
          )}
          <details className="bg-slate-800/50 border border-slate-700 rounded p-3">
            <summary className="cursor-pointer text-sm font-medium">Full reconciliation output</summary>
            <pre className="mt-2 overflow-x-auto text-xs">
              {JSON.stringify(result, null, 2)}
            </pre>
          </details>
        </div>
      )}
    </div>
  );
}
