import React from 'react';
import { ShieldAlert, Cpu, Database, Activity, RefreshCw } from 'lucide-react';

export default function Navbar({ health, onRefreshHealth, onOpenHealthModal }) {
  const isHealthy = health && health.status === 'healthy';

  return (
    <header className="border-b border-slate-800 bg-[#0c1220]/80 backdrop-blur-md sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand */}
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-emerald-500 to-teal-400 flex items-center justify-center shadow-lg shadow-emerald-500/20">
            <ShieldAlert className="w-6 h-6 text-slate-950 stroke-[2.2]" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-bold text-lg tracking-tight text-white">
                Contract<span className="text-emerald-400">Lens</span>
              </span>
              <span className="text-[10px] font-semibold tracking-wider uppercase px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                AI Risk Intelligence
              </span>
            </div>
            <p className="text-xs text-slate-400 hidden sm:block">
              In-Memory FAISS Vector RAG • Zero-DB Architecture
            </p>
          </div>
        </div>

        {/* Live Backend & Memory Indicators */}
        <div className="flex items-center space-x-3">
          {/* In-Memory stats tag */}
          {health && (
            <div className="hidden md:flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-slate-900/80 border border-slate-800 text-xs text-slate-300">
              <Database className="w-3.5 h-3.5 text-emerald-400" />
              <span>
                Memory:{' '}
                <strong className="text-white">
                  {health.in_memory_documents_count || 0}
                </strong>{' '}
                docs ({health.faiss_indexes_count || 0} FAISS index)
              </span>
            </div>
          )}

          {/* Health Pill Button */}
          <button
            onClick={onOpenHealthModal}
            className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg border text-xs font-medium transition-all ${
              isHealthy
                ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/20'
                : 'bg-rose-500/10 border-rose-500/30 text-rose-400 hover:bg-rose-500/20'
            }`}
          >
            <span
              className={`w-2 h-2 rounded-full ${
                isHealthy ? 'bg-emerald-400 animate-pulse' : 'bg-rose-400'
              }`}
            />
            <span>{isHealthy ? 'FastAPI & FAISS Live' : 'Connecting Backend...'}</span>
          </button>

          {/* Manual Refresh Button */}
          <button
            onClick={onRefreshHealth}
            title="Refresh System Health"
            className="p-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-white hover:bg-slate-800 transition"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>
    </header>
  );
}
