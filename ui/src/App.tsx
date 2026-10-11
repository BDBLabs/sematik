// src/App.tsx — main layout with tab navigation
import React, { useEffect, useState } from "react";
import { health } from "./api";
import DataUpload from "./components/DataUpload";
import Profiler from "./components/Profiler";
import MappingEditor from "./components/MappingEditor";
import Compiler from "./components/Compiler";
import Executor from "./components/Executor";
import Reconciler from "./components/Reconciler";
import EntropyPane from "./components/EntropyPane";
import CandidateRelationships from "./components/CandidateRelationships";

type Tab = "upload" | "profile" | "mapping" | "compile" | "execute" | "reconcile" | "entropy" | "candidates";

const TABS: { id: Tab; label: string; desc: string }[] = [
  { id: "upload", label: "Data Upload", desc: "Upload source rows or load the fixture" },
  { id: "profile", label: "Profiler", desc: "Profile columns and view discovery hypotheses" },
  { id: "mapping", label: "Mapping", desc: "Create and inspect an approved Mapping (§13)" },
  { id: "compile", label: "Compiler", desc: "Compile to Python plan + SQL SELECT (§19)" },
  { id: "execute", label: "Executor", desc: "Run conversion, view lineage & manifest (§29)" },
  { id: "reconcile", label: "Reconciler", desc: "Population + record reconciliation (§30)" },
  { id: "entropy", label: "Entropy", desc: "Semantic entropy & uncertainty (§76)" },
  { id: "candidates", label: "FK Candidates", desc: "Heuristic FK relationships (§12)" },
];

export default function App() {
  const [tab, setTab] = useState<Tab>("upload");
  const [online, setOnline] = useState(false);

  useEffect(() => {
    health().then(() => setOnline(true)).catch(() => setOnline(false));
  }, []);

  // Shared state that flows through the lifecycle
  const [rows, setRows] = useState<any[]>([]);
  const [currentMapping, setCurrentMapping] = useState<any>(null);
  const [currentSteps, setCurrentSteps] = useState<any[]>([]);
  const [execResult, setExecResult] = useState<any>(null);
  const [profileResults, setProfileResults] = useState<Record<string, any>>({});

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100">
      <header className="bg-slate-800 border-b border-slate-700 px-6 py-4 flex items-center justify-between">
        <h1 className="text-xl font-semibold">sematik — Semantic Conversion Engine</h1>
        <span className={`text-xs px-2 py-1 rounded ${online ? "bg-green-900/30 text-green-400" : "bg-red-900/30 text-red-400"}`}>
          {online ? "API online" : "API offline"}
        </span>
      </header>

      <nav className="bg-slate-800 border-b border-slate-700 px-2 flex overflow-x-auto">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`px-4 py-3 text-sm font-medium border-b-2 transition ${
              tab === t.id
                ? "border-blue-400 text-blue-300"
                : "border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-600"
            }`}
            title={t.desc}
          >
            {t.label}
          </button>
        ))}
      </nav>

      <main className="p-6 max-w-6xl mx-auto">
        {tab === "upload" && <DataUpload rows={rows} setRows={setRows} />}
        {tab === "profile" && <Profiler rows={rows} results={profileResults} setResults={setProfileResults} />}
        {tab === "mapping" && (
          <MappingEditor
            rows={rows}
            mapping={currentMapping}
            setMapping={setCurrentMapping}
            steps={currentSteps}
            setSteps={setCurrentSteps}
          />
        )}
        {tab === "compile" && <Compiler mapping={currentMapping} steps={currentSteps} />}
        {tab === "execute" && <Executor mapping={currentMapping} steps={currentSteps} rows={rows} result={execResult} setResult={setExecResult} />}
        {tab === "reconcile" && <Reconciler rows={rows} execResult={execResult} />}
        {tab === "entropy" && <EntropyPane profileResults={profileResults} />}
        {tab === "candidates" && <CandidateRelationships rows={rows} />}
      </main>
    </div>
  );
}
