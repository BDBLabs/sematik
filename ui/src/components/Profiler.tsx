// src/components/Profiler.tsx
import React, { useState } from "react";
import { profileColumn, getHypotheses } from "../api";

interface Props {
  rows: any[];
  results: Record<string, any>;
  setResults: (r: Record<string, any>) => void;
}

export default function Profiler({ rows, results, setResults }: Props) {
  const [column, setColumn] = useState("");
  const [loading, setLoading] = useState(false);

  const columns = rows.length > 0 ? Object.keys(rows[0]) : [];

  const run = async () => {
    if (!column) return;
    setLoading(true);
    try {
      const values = rows.map((r) => r[column]);
      const prof = await profileColumn(column, values);
      const hyps = await getHypotheses(column, values);
      setResults({ ...results, [column]: { profile: prof, hypotheses: hyps } });
    } catch (e) {
      alert(`Failed: ${e}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">Column Profiler</h2>
      <div className="flex gap-2">
        <select
          value={column}
          onChange={(e) => setColumn(e.target.value)}
          className="flex-1 bg-slate-800 border border-slate-700 rounded px-3 py-2"
        >
          <option value="">Select a column</option>
          {columns.map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
        <button
          onClick={run}
          disabled={!column || loading || rows.length === 0}
          className="px-4 py-2 bg-blue-600 rounded hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? "Profiling…" : "Profile + Hypotheses"}
        </button>
      </div>

      {results[column] && (
        <div className="space-y-3">
          <div>
            <h3 className="font-medium mb-1">Profile: {column}</h3>
            <pre className="bg-slate-800/50 border border-slate-700 rounded p-3 overflow-x-auto text-sm">
              {JSON.stringify(results[column].profile, null, 2)}
            </pre>
          </div>
          <div>
            <h3 className="font-medium mb-1">Discovery Hypotheses</h3>
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-700">
                  <th className="pb-2">Concept</th>
                  <th className="pb-2">Meaning</th>
                  <th className="pb-2">Strength</th>
                  <th className="pb-2">Calibrated?</th>
                  <th className="pb-2">Evidence Basis</th>
                </tr>
              </thead>
              <tbody>
                {results[column].hypotheses.map((h: any, i: number) => (
                  <tr key={i} className="border-b border-slate-800">
                    <td className="py-1.5">{h.concept}</td>
                    <td className="py-1.5">{h.candidate_meaning}</td>
                    <td className="py-1.5">{h.confidence.overall}</td>
                    <td className="py-1.5">
                      <span className={h.confidence.calibrated
                        ? "text-green-400" : "text-amber-400"}>
                        {h.confidence.calibrated ? "Yes" : "No (heuristic)"}
                      </span>
                    </td>
                    <td className="py-1.5 text-slate-400 text-xs">{h.evidence_basis}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
