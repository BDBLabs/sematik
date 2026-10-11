// src/components/DataUpload.tsx
import React, { useState } from "react";
import { loadFixture } from "../api";

interface Props {
  rows: any[];
  setRows: (r: any[]) => void;
}

export default function DataUpload({ rows, setRows }: Props) {
  const [loading, setLoading] = useState(false);

  const loadFixtureRow = async (name: string) => {
    setLoading(true);
    try {
      const data = await loadFixture(name);
      if (Array.isArray(data)) setRows(data);
      else setRows((data as any).rows || []);
    } catch (e) {
      alert(`Failed to load fixture: ${e}`);
    } finally {
      setLoading(false);
    }
  };

  const handlePaste = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const text = e.target.value.trim();
    if (!text) return;
    try {
      const parsed = JSON.parse(text);
      setRows(Array.isArray(parsed) ? parsed : (parsed.rows || []));
    } catch {
      setRows(text.split("\n").map((l) => ({ value: l.trim() })).filter((r) => r.value));
    }
  };

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">Source Data</h2>
      <p className="text-sm text-slate-400">
        Paste JSON array of rows, or load a fixture. Rows are plain key/value dicts.
      </p>
      <div className="grid grid-cols-2 gap-4">
        <button onClick={() => loadFixtureRow("legacy_parcels")} disabled={loading}
          className="px-4 py-2 bg-blue-600 rounded hover:bg-blue-700 disabled:opacity-50">
          {loading ? "Loading…" : "Load legacy_parcels fixture"}
        </button>
        <button onClick={() => loadFixtureRow("demo-mapping")} disabled={loading}
          className="px-4 py-2 bg-slate-700 rounded hover:bg-slate-600 disabled:opacity-50">
          Load demo mapping fixture
        </button>
      </div>
      <textarea
        placeholder='[{"_id": "r1", "APN": "A-1", "LNDVAL": 100000, "AV_IMP": 100000, "XFER": "REG"}, ...]'
        onChange={handlePaste}
        className="w-full h-40 bg-slate-800 border border-slate-700 rounded p-3 font-mono text-sm resize-y focus:outline-none focus:border-blue-500"
        defaultValue={JSON.stringify([
          { _id: "r1", APN: "A-1", LNDVAL: 100000, AV_IMP: 100000, XFER: "REG" },
          { _id: "r2", APN: "A-2", LNDVAL: 200000, AV_IMP: 50000, XFER: "REG" },
        ], null, 2)}
      />
      {rows.length > 0 && (
        <p className="text-sm text-slate-400">{rows.length} rows loaded</p>
      )}
    </div>
  );
}
