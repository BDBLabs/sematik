// src/components/EntropyPane.tsx
import React, { useState } from "react";
import { conceptEntropy, semanticEntropy, semanticEntropyFlagged } from "../api";
import type { Row } from "../api";

interface Props {
  profileResults: Record<string, any>;
}

export default function EntropyPane({ profileResults }: Props) {
  const [loading, setLoading] = useState(false);
  const [conceptResult, setConceptResult] = useState<any>(null);
  const [semanticResult, setSemanticResult] = useState<any>(null);
  const [flaggedResult, setFlaggedResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const columns = Object.keys(profileResults);

  // Build hypotheses from stored profile results
  const buildHyps = (cols: string[]) => {
    const hyps: any[] = [];
    cols.forEach((col) => {
      const hr = profileResults[col]?.hypotheses || [];
      hyps.push(...hr);
    });
    // Fill in default evidence_basis if missing
    return hyps.map((h) => ({
      ...h,
      evidence_basis: h.evidence_basis || "profiler",
      confidence: { ...h.confidence, calibrated: h.confidence?.calibrated ?? true },
    }));
  };

  const runConcept = async () => {
    if (columns.length === 0) return;
    setLoading(true); setError(null);
    try {
      const r = await conceptEntropy(buildHyps(columns));
      setConceptResult(r);
    } catch (e: any) { setError(e.message); } finally { setLoading(false); }
  };

  const runSemantic = async () => {
    if (columns.length === 0) return;
    setLoading(true); setError(null);
    try {
      const r = await semanticEntropy(buildHyps(columns));
      setSemanticResult(r);
    } catch (e: any) { setError(e.message); } finally { setLoading(false); }
  };

  const runFlagged = async () => {
    if (columns.length === 0) return;
    setLoading(true); setError(null);
    try {
      const r = await semanticEntropyFlagged(buildHyps(columns));
      setFlaggedResult(r);
    } catch (e: any) { setError(e.message); } finally { setLoading(false); }
  };

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">Entropy & Uncertainty (§76)</h2>
      <p className="text-sm text-slate-400">
        Compute concept-level and semantic-level entropy from discovery hypotheses.
        Requires profiled columns (see Profiler tab).
      </p>

      {columns.length === 0 && (
        <p className="text-sm text-slate-400">No profiled columns yet. Profile some columns first.</p>
      )}

      <div className="flex gap-2 flex-wrap">
        <button onClick={runConcept} disabled={loading || columns.length === 0}
          className="px-4 py-2 bg-blue-600 rounded hover:bg-blue-700 disabled:opacity-50">
          Concept Entropy
        </button>
        <button onClick={runSemantic} disabled={loading || columns.length === 0}
          className="px-4 py-2 bg-cyan-600 rounded hover:bg-cyan-700 disabled:opacity-50">
          Semantic Entropy
        </button>
        <button onClick={runFlagged} disabled={loading || columns.length === 0}
          className="px-4 py-2 bg-amber-600 rounded hover:bg-amber-700 disabled:opacity-50">
          Semantic Entropy (Flagged)
        </button>
      </div>

      {error && (
        <pre className="bg-red-900/30 border border-red-700 rounded p-3 text-sm text-red-300">
          {error}
        </pre>
      )}

      {conceptResult && conceptResult.entropy !== undefined && (
        <div className="space-y-2">
          <h3 className="font-medium">Concept Entropy</h3>
          <p className="text-sm"><span className="text-slate-400">entropy:</span> <span className="font-mono">{conceptResult.entropy}</span></p>
          <pre className="bg-slate-800/50 border border-slate-700 rounded p-3 text-xs overflow-x-auto">
            {JSON.stringify(conceptResult, null, 2)}
          </pre>
        </div>
      )}

      {semanticResult && semanticResult.entropy !== undefined && (
        <div className="space-y-2">
          <h3 className="font-medium">Semantic Entropy</h3>
          <p className="text-sm"><span className="text-slate-400">entropy:</span> <span className="font-mono">{semanticResult.entropy}</span></p>
        </div>
      )}

      {flaggedResult && flaggedResult.entropy !== undefined && (
        <div className="space-y-2">
          <h3 className="font-medium">Semantic Entropy (Flagged)</h3>
          <p className="text-sm"><span className="text-slate-400">entropy:</span> <span className="font-mono">{flaggedResult.entropy}</span></p>
          {flaggedResult.warnings?.length > 0 && (
            <ul className="list-disc list-inside text-sm text-amber-300">
              {flaggedResult.warnings.map((w: string, i: number) => (
                <li key={i}>{w}</li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
