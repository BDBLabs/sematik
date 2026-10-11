// src/components/Compiler.tsx
import React, { useState } from "react";
import { compilePlan, compileSql } from "../api";
import type { MappingIn, StepIn } from "../api";

interface Props {
  mapping: MappingIn | null;
  steps: StepIn[];
}

export default function Compiler({ mapping, steps }: Props) {
  const [loading, setLoading] = useState(false);
  const [pythonResult, setPythonResult] = useState<any>(null);
  const [sqlResult, setSqlResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const runPython = async () => {
    if (!mapping) return;
    setLoading(true); setError(null);
    try {
      const r = await compilePlan(mapping, steps);
      setPythonResult(r);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const runSql = async () => {
    if (!mapping) return;
    setLoading(true); setError(null);
    try {
      const r = await compileSql(mapping, steps, mapping.source_artifact || "source", "postgres");
      setSqlResult(r);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  if (!mapping) {
    return (
      <div className="space-y-4">
        <h2 className="text-lg font-semibold">Compiler (§19)</h2>
        <p className="text-sm text-slate-400">No mapping loaded. Create one in the Mapping tab first.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">Compiler (§19)</h2>
      <div className="flex gap-2">
        <button onClick={runPython} disabled={loading || steps.length === 0}
          className="px-4 py-2 bg-blue-600 rounded hover:bg-blue-700 disabled:opacity-50">
          Compile → Python plan
        </button>
        <button onClick={runSql} disabled={loading || steps.length === 0}
          className="px-4 py-2 bg-cyan-600 rounded hover:bg-cyan-700 disabled:opacity-50">
          Compile → SQL SELECT
        </button>
      </div>

      {error && (
        <pre className="bg-red-900/30 border border-red-700 rounded p-3 text-sm text-red-300 overflow-x-auto">
          {error}
        </pre>
      )}

      {pythonResult && (
        <div className="space-y-2">
          <h3 className="font-medium">Compiled Plan</h3>
          <pre className="bg-slate-800/50 border border-slate-700 rounded p-3 overflow-x-auto text-sm">
            {JSON.stringify(pythonResult, null, 2)}
          </pre>
        </div>
      )}

      {sqlResult && (
        <div className="space-y-2">
          <h3 className="font-medium">SQL SELECT</h3>
          <pre className="bg-slate-800/50 border border-slate-700 rounded p-3 overflow-x-auto text-sm font-mono">
            {sqlResult.sql}
          </pre>
        </div>
      )}
    </div>
  );
}
