// src/components/MappingEditor.tsx
import React, { useState } from "react";
import { mappingDigest, loadFixture } from "../api";
import type { MappingIn, StepIn, Row } from "../api";

interface Props {
  rows: Row[];
  mapping: MappingIn | null;
  setMapping: (m: MappingIn) => void;
  steps: StepIn[];
  setSteps: (s: StepIn[]) => void;
}

const SEVEN_LEVELS = [
  { level: 1, kind: "physical", label: "Physical source" },
  { level: 2, kind: "semantic", label: "Semantic meaning" },
  { level: 3, kind: "canonical", label: "Canonical concept" },
  { level: 4, kind: "context", label: "Context" },
  { level: 5, kind: "temporal", label: "Temporal" },
  { level: 6, kind: "authority", label: "Authority" },
  { level: 7, kind: "target", label: "Target artifact" },
];

export default function MappingEditor({ rows, mapping, setMapping, steps, setSteps }: Props) {
  const [loading, setLoading] = useState(false);

  const loadDemo = async () => {
    setLoading(true);
    try {
      const m = await loadFixture("demo-mapping") as any;
      setMapping(m);
      const s = await loadFixture("demo-steps") as any[];
      setSteps(s);
    } catch (e) {
      alert(`Failed: ${e}`);
    } finally {
      setLoading(false);
    }
  };

  const updateMapping = (patch: Partial<MappingIn>) => {
    setMapping({ ...(mapping || {}), ...patch });
  };

  const updateLevel = (i: number, field: string, value: string) => {
    if (!mapping) return;
    const levels = [...(mapping.levels || [])];
    levels[i] = { ...levels[i], [field]: value };
    updateMapping({ levels });
  };

  const addLevel = () => {
    if (!mapping) return;
    const levels = [...(mapping.levels || [])];
    levels.push({ level: levels.length + 1, kind: "", statement: "" });
    updateMapping({ levels });
  };

  if (!mapping) {
    return (
      <div className="space-y-4">
        <h2 className="text-lg font-semibold">Mapping Editor</h2>
        <button onClick={loadDemo} disabled={loading}
          className="px-4 py-2 bg-blue-600 rounded hover:bg-blue-700">
          {loading ? "Loading…" : "Load demo mapping (7 levels, approved)"}
        </button>
        <p className="text-sm text-slate-400">
          Or build manually — fill out the form below.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-lg font-semibold">Mapping Editor (§13)</h2>
        <button onClick={loadDemo} disabled={loading}
          className="px-3 py-1 bg-slate-700 rounded hover:bg-slate-600 text-sm">
          Reset to demo
        </button>
      </div>

      {/* Core fields */}
      <div className="grid grid-cols-2 gap-4">
        <input type="text" placeholder="Source artifact"
          value={mapping.source_artifact}
          onChange={(e) => updateMapping({ source_artifact: e.target.value })}
          className="bg-slate-800 border border-slate-700 rounded px-3 py-2" />
        <input type="text" placeholder="Canonical concept"
          value={mapping.canonical_concept || ""}
          onChange={(e) => updateMapping({ canonical_concept: e.target.value })}
          className="bg-slate-800 border border-slate-700 rounded px-3 py-2" />
        <input type="text" placeholder="Target artifact"
          value={mapping.target_artifact || ""}
          onChange={(e) => updateMapping({ target_artifact: e.target.value })}
          className="bg-slate-800 border border-slate-700 rounded px-3 py-2" />
        <input type="text" placeholder="Version"
          value={mapping.version || ""}
          onChange={(e) => updateMapping({ version: e.target.value })}
          className="bg-slate-800 border border-slate-700 rounded px-3 py-2" />
      </div>

      {/* Approval fields */}
      <div className="grid grid-cols-2 gap-4">
        <input type="text" placeholder="Approved by"
          value={mapping.approved_by || ""}
          onChange={(e) => updateMapping({ approved_by: e.target.value })}
          className="bg-slate-800 border border-slate-700 rounded px-3 py-2" />
        <input type="text" placeholder="Approval ref"
          value={mapping.approval_ref || ""}
          onChange={(e) => updateMapping({ approval_ref: e.target.value })}
          className="bg-slate-800 border border-slate-700 rounded px-3 py-2" />
        <input type="text" placeholder="Evidence refs (comma-separated)"
          value={(mapping.evidence_refs || []).join(", ")}
          onChange={(e) => updateMapping({ evidence_refs: e.target.value.split(",").map((s) => s.trim()).filter(Boolean) })}
          className="bg-slate-800 border border-slate-700 rounded px-3 py-2" />
        <input type="text" placeholder="Golden plan digest"
          value={mapping.golden_plan_digest || ""}
          onChange={(e) => updateMapping({ golden_plan_digest: e.target.value })}
          className="bg-slate-800 border border-slate-700 rounded px-3 py-2" />
      </div>

      {/* Confidence */}
      <div className="flex gap-2 items-center">
        <label className="text-sm">Confidence:</label>
        <input type="number" min="0" max="1" step="0.01"
          value={mapping.confidence?.overall ?? 1.0}
          onChange={(e) => updateMapping({ confidence: { ...(mapping.confidence || {}), overall: parseFloat(e.target.value) || 0 }})}
          className="w-16 bg-slate-800 border border-slate-700 rounded px-2 py-1" />
        <label className="text-sm">Drivers (comma-separated):</label>
        <input type="text"
          value={(mapping.confidence?.drivers || []).join(", ")}
          onChange={(e) => updateMapping({ confidence: { ...(mapping.confidence || {}), overall: mapping.confidence?.overall ?? 1.0, drivers: e.target.value.split(",").map((s) => s.trim()).filter(Boolean) }})}
          className="flex-1 bg-slate-800 border border-slate-700 rounded px-2 py-1 text-sm" />
        <label className="flex items-center gap-1 text-sm">
          <input type="checkbox"
            checked={mapping.confidence?.calibrated ?? true}
            onChange={(e) => updateMapping({ confidence: { ...(mapping.confidence || {}), overall: mapping.confidence?.overall ?? 1.0, calibrated: e.target.checked }})}
          />
          Calibrated
        </label>
      </div>

      {/* Seven levels */}
      <div>
        <h3 className="font-medium mb-2">Seven Semantic Levels (§13)</h3>
        <div className="space-y-2">
          {(mapping.levels || []).map((lv, i) => (
            <div key={i} className="flex gap-2 items-start">
              <input type="number" min="1" max="7"
                value={lv.level}
                onChange={(e) => updateLevel(i, "level", e.target.value)}
                className="w-12 bg-slate-800 border border-slate-700 rounded px-1 py-1" />
              <input type="text" placeholder="kind"
                value={lv.kind || ""}
                onChange={(e) => updateLevel(i, "kind", e.target.value)}
                className="w-24 bg-slate-800 border border-slate-700 rounded px-1 py-1 text-sm" />
              <input type="text" placeholder="statement"
                value={lv.statement || ""}
                onChange={(e) => updateLevel(i, "statement", e.target.value)}
                className="flex-1 bg-slate-800 border border-slate-700 rounded px-2 py-1 text-sm" />
            </div>
          ))}
        </div>
        <button onClick={addLevel}
          className="mt-2 px-3 py-1 bg-slate-700 rounded hover:bg-slate-600 text-sm">
          + Add level
        </button>
      </div>

      {/* Steps */}
      <div>
        <h3 className="font-medium mb-2">Transformation Steps</h3>
        <div className="space-y-1">
          {steps.map((s, i) => (
            <div key={i} className="font-mono text-sm bg-slate-800/50 rounded p-2">
              {s.op}({JSON.stringify(s.args)})
            </div>
          ))}
        </div>
      </div>

      {/* Approval check */}
      <button
        onClick={checkApproval}
        className="px-4 py-2 bg-blue-600 rounded hover:bg-blue-700"
      >
        Check approval status
      </button>
    </div>
  );
}
