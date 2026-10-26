import React from 'react';
import { X, CheckCircle2, AlertCircle, Cpu, HardDrive, ShieldCheck, Zap } from 'lucide-react';

export default function HealthModal({ health, onClose }) {
  if (!health) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fadeIn">
      <div className="glass-panel w-full max-w-lg rounded-2xl p-6 border border-slate-700 shadow-2xl relative">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center space-x-3 mb-5">
          <div className="w-10 h-10 rounded-xl bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-white">System Architecture & Health</h3>
            <p className="text-xs text-slate-400">Live inspection of backend state & in-memory indexes</p>
          </div>
        </div>

        <div className="space-y-3">
          {/* Status card */}
          <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 flex items-center justify-between">
            <span className="text-sm text-slate-300">FastAPI Service Status</span>
            <span className="inline-flex items-center space-x-1.5 text-xs font-semibold px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>{health.status.toUpperCase()}</span>
            </span>
          </div>

          {/* In-Memory Store stats */}
          <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-slate-200 flex items-center space-x-2">
                <HardDrive className="w-4 h-4 text-emerald-400" />
                <span>In-Memory State Store</span>
              </span>
              <span className="text-xs text-emerald-400 font-mono">No Database Mode</span>
            </div>
            <div className="grid grid-cols-2 gap-2 text-xs pt-1 border-t border-slate-800">
              <div>
                <span className="text-slate-400">Active Contracts:</span>{' '}
                <strong className="text-white">{health.in_memory_documents_count}</strong>
              </div>
              <div>
                <span className="text-slate-400">FAISS Vector Indexes:</span>{' '}
                <strong className="text-white">{health.faiss_indexes_count}</strong>
              </div>
            </div>
          </div>

          {/* Hosted AI Services status */}
          <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-slate-200 flex items-center space-x-2">
                <Zap className="w-4 h-4 text-amber-400" />
                <span>Google Gemini AI</span>
              </span>
              <span className="text-[11px] font-mono text-emerald-400">
                {health.gemini_model || 'gemini-2.0-flash'}
              </span>
            </div>

            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="p-2 rounded bg-slate-950/50 border border-slate-800/80">
                <div className="text-slate-400 mb-1">Gemini LLM</div>
                <div className="flex items-center space-x-1">
                  {health.llm_configured ? (
                    <span className="text-emerald-400 font-medium">Active (API Key Set)</span>
                  ) : (
                    <span className="text-amber-400 font-medium">Heuristic Legal Mode</span>
                  )}
                </div>
              </div>

              <div className="p-2 rounded bg-slate-950/50 border border-slate-800/80">
                <div className="text-slate-400 mb-1">Gemini Embeddings</div>
                <div className="flex items-center space-x-1">
                  {health.embedding_configured ? (
                    <span className="text-emerald-400 font-medium">text-embedding-004</span>
                  ) : (
                    <span className="text-amber-400 font-medium">In-Memory Cosine</span>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Model Context Protocol (MCP) status */}
          <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-slate-200 flex items-center space-x-2">
                <Cpu className="w-4 h-4 text-indigo-400" />
                <span>Model Context Protocol (MCP)</span>
              </span>
              <span className={`text-[11px] font-mono ${health.mcp_enabled ? 'text-indigo-400' : 'text-slate-400'}`}>
                {health.mcp_enabled ? `Transport: ${health.mcp_transport}` : 'Disabled'}
              </span>
            </div>

            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="p-2 rounded bg-slate-950/50 border border-slate-800/80">
                <div className="text-slate-400 mb-1">MCP Integration</div>
                <div className="flex items-center space-x-1">
                  {health.mcp_enabled ? (
                    <span className="text-emerald-400 font-medium">Enabled</span>
                  ) : (
                    <span className="text-slate-400 font-medium">Disabled (Contract Only)</span>
                  )}
                </div>
              </div>

              <div className="p-2 rounded bg-slate-950/50 border border-slate-800/80">
                <div className="text-slate-400 mb-1">Server Command</div>
                <div className="truncate text-slate-300 font-mono text-[10px]">
                  {health.mcp_server_command || 'Not configured'}
                </div>
              </div>
            </div>
          </div>

          {/* Runtime Info */}
          <div className="p-3 rounded-xl bg-slate-900/40 border border-slate-800 text-xs text-slate-400 space-y-1">
            <div className="flex justify-between">
              <span>Environment:</span>
              <span className="text-slate-200 font-mono">{health.environment}</span>
            </div>
            <div className="flex justify-between">
              <span>Uptime:</span>
              <span className="text-slate-200 font-mono">{Math.round(health.uptime_seconds)}s</span>
            </div>
          </div>
        </div>

        <div className="mt-5 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-sm font-medium text-slate-200 transition"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
