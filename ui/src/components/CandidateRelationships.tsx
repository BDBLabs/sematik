// src/components/CandidateRelationships.tsx
import React, { useState } from "react";
import { getCandidates } from "../api";
import type { Row } from "../api";

interface Props {
  rows: Row[];
}

export default function CandidateRelationships({ rows }: Props) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Group rows by column name to form "tables"
  const tables: Record<string, Row[]> = rows.length > 0 ? { source: rows } : {};

  const run = async () => {
    if (!rows.length) return;
    setLoading(true); setError(null);
    try {
      const r = await getCandidates(tables);
      setResult(r);
    } catch (e: any) { setError(e.message); } finally { setLoading(false); }
  };

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">Candidate Relationships (§12)</h2>
      <p className="text-sm text-slate-400">
        Heuristic FK detection: finds columns with high value overlap across tables.
      </p>

      <button onClick={run}
        disabled={loading || rows.length === 0}
        className="px-4 py-2 bg-blue-600 rounded hover:bg-blue-700 disabled:opacity-50">
        {loading ? "Detecting…" : "Detect Candidate FKs"}
      </button>

      {error && (
        <pre className="bg-red-900/30 border border-red-700 rounded p-3 text-sm text-red-300">{error}</pre>
      )}

      {result && result.length > 0 && (
        <div className="space-y-2">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-slate-700">
                <th className="pb-2">Source Table</th>
                <th className="pb-2">Source Column</th>
                <th className="pb-2">→</th>
                <th className="pb-2">Target Table</th>
                <th className="pb-2">Target Column</th>
                <th className="pb-2">Overlap</th>
                <th className="pb-2">Confidence</th>
              </tr>
            </thead>
            <tbody>
              {result.map((c, i) => (
                <tr key={i} className="border-b border-slate-800">
                  <td className="py-1.5">{c.source_table}</td>
                  <td className="py-1.5">{c.source_key}</td>
                  <td className="py-1.5">→</td>
                  <td className="py-1.5">{c.target_table}</td>
                  <td className="py-1.5">{c.target_key}</td>
                  <td className="py-1.5">{c.overlap.toFixed(3)}</td>
                  <td className="py-1.5">
                    {c.confidence.overall}
                    <span className={`ml-1 text-xs ${c.confidence.calibrated ? "text-green-400" : "text-amber-400"}`}>
                      {c.confidence.calibrated ? "✓" : "✗ heuristic"}
                    </span>
                    <span className="text-xs text-slate-500 block">{c.confidence.drivers.join(", ")}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <details className="bg-slate-800/50 border border-slate-700 rounded p-3">
            <summary className="cursor-pointer text-sm font-medium">Raw output</summary>
            <pre className="mt-2 overflow-x-auto text-xs">
              {JSON.stringify(result, null, 2)}
            </pre>
          </details>
        </div>
      )}

      {result && result.length === 0 && rows.length > 0 && (
        <p className="text-sm text-slate-400">No candidate relationships found above the 0.9 overlap threshold.</p>
      )}
    </div>
  );
}
