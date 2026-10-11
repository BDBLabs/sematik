// src/components/Executor.tsx
import React, { useState } from "react";
import { executePlan, exportCsv, exportJson } from "../api";
import type { MappingIn, StepIn, Row } from "../api";

interface Props {
  mapping: MappingIn | null;
  steps: StepIn[];
  rows: Row[];
  result: any;
  setResult: (r: any) => void;
}

export default function Executor({ mapping, steps, rows, result, setResult }: Props) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showGolden, setShowGolden] = useState(false);
  const [goldenJson, setGoldenJson] = useState("");

  const run = async () => {
    if (!mapping || rows.length === 0) return;
    setLoading(true); setError(null);
    try {
      let golden: any[] | undefined;
      if (showGolden && goldenJson.trim()) {
        golden = JSON.parse(goldenJson);
      }
      const r = await executePlan({
        mapping, steps, rows,
        require_golden: showGolden && !!golden,
        golden,
      });
      setResult(r);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">Executor (§29)</h2>
      {rows.length === 0 && (
        <p className="text-sm text-slate-400">No rows loaded. Go to Data Upload first.</p>
      )}
      {!mapping && (
        <p className="text-sm text-slate-400">No mapping loaded. Create one in the Mapping tab.</p>
      )}

      <div className="flex items-center gap-4">
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox"
            checked={showGolden}
            onChange={(e) => setShowGolden(e.target.checked)}
          />
          Use golden records
        </label>
      </div>

      {showGolden && (
        <textarea
          placeholder='[{"name": "g1", "input": {"_id": "r1", "APN": "A-1", "LNDVAL": 100000}, "expected": {"apn": "A-1"}}]'
          value={goldenJson}
          onChange={(e) => setGoldenJson(e.target.value)}
          className="w-full h-24 bg-slate-800 border border-slate-700 rounded p-2 font-mono text-sm resize-y"
        />
      )}

      <button onClick={run}
        disabled={loading || rows.length === 0 || !mapping || steps.length === 0}
        className="px-4 py-2 bg-blue-600 rounded hover:bg-blue-700 disabled:opacity-50">
        {loading ? "Executing…" : "Run Conversion"}
      </button>

      {error && (
        <pre className="bg-red-900/30 border border-red-700 rounded p-3 text-sm text-red-300 overflow-x-auto">
          {error}
        </pre>
      )}

      {result && (
        <div className="space-y-3">
          <div className="grid grid-cols-4 gap-4 text-center">
            <div><span className="text-2xl font-bold text-blue-400">{result.converted}</span><div className="text-xs text-slate-400">Converted</div></div>
            <div><span className="text-2xl font-bold text-amber-400">{result.rejected}</span><div className="text-xs text-slate-400">Rejected</div></div>
            <div><span className="text-2xl font-bold text-slate-300">{result.total}</span><div className="text-xs text-slate-400">Total</div></div>
            <div><span className="text-2xl font-bold text-cyan-400">{result.manifest_hash?.slice(0, 12)}</span><div className="text-xs text-slate-400">Manifest</div></div>
          </div>

          {result.outputs?.length > 0 && (
            <div className="flex gap-2">
              <button
                onClick={() => exportCsv(result.outputs, "sematik_converted.csv")}
                className="px-3 py-1 bg-green-600 rounded hover:bg-green-700 text-sm"
              >
                Download CSV
              </button>
              <button
                onClick={() => exportJson(result.outputs, "sematik_converted.json")}
                className="px-3 py-1 bg-green-600 rounded hover:bg-green-700 text-sm"
              >
                Download JSON
              </button>
            </div>
          )}

          {result.exceptions?.length > 0 && (
            <div className="space-y-1">
              <h3 className="font-medium text-amber-400">Exceptions ({result.exceptions.length})</h3>
              {result.exceptions.map((e: any, i: number) => (
                <div key={i} className="bg-amber-900/20 border border-amber-800 rounded p-2 text-sm">
                  <span className="text-amber-300">{e.phase}</span>: {e.row_id} — {e.error}
                </div>
              ))}
            </div>
          )}

          {result.converted_rows && (
            <details className="bg-slate-800/50 border border-slate-700 rounded p-3">
              <summary className="cursor-pointer text-sm font-medium">View converted rows</summary>
              <pre className="mt-2 overflow-x-auto text-xs">
                {JSON.stringify(result.converted_rows, null, 2)}
              </pre>
            </details>
          )}

          {result.provenance && (
            <details className="bg-slate-800/50 border border-slate-700 rounded p-3">
              <summary className="cursor-pointer text-sm font-medium">View provenance / lineage</summary>
              <pre className="mt-2 overflow-x-auto text-xs">
                {JSON.stringify(result.provenance, null, 2)}
              </pre>
            </details>
          )}
        </div>
      )}
    </div>
  );
}
