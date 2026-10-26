import React, { useState } from 'react';
import {
  AlertCircle,
  ChevronDown,
  ChevronUp,
  Copy,
  Check,
  ShieldCheck,
  Scale,
  Target,
  FileQuestion,
  HelpCircle,
  Layers,
  Search,
  Filter,
  CheckCircle2,
  XCircle,
} from 'lucide-react';

export default function ClauseInspector({ clauses, contractId, onSelectCitation }) {
  const [riskFilter, setRiskFilter] = useState('ALL');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedId, setExpandedId] = useState(null);
  const [copiedId, setCopiedId] = useState(null);

  if (!clauses || clauses.length === 0) {
    return (
      <div className="glass-panel rounded-2xl p-8 text-center text-slate-400">
        No clause analysis available yet for this agreement.
      </div>
    );
  }

  const filteredClauses = clauses.filter((c) => {
    // Risk priority filter
    if (riskFilter !== 'ALL' && c.risk_level !== riskFilter && c.review_priority !== riskFilter) {
      return false;
    }
    // Presence status filter
    if (statusFilter !== 'ALL' && c.presence_status !== statusFilter) {
      return false;
    }
    // Search query
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const titleMatch = c.clause_title?.toLowerCase().includes(q);
      const catMatch = c.category?.toLowerCase().includes(q);
      const textMatch = c.original_text?.toLowerCase().includes(q);
      const expMatch = (c.explanation || c.risk_reasoning)?.toLowerCase().includes(q);
      return titleMatch || catMatch || textMatch || expMatch;
    }
    return true;
  });

  const getPriorityStyle = (level) => {
    switch (level) {
      case 'CRITICAL':
        return 'bg-rose-500/10 border-rose-500/30 text-rose-400';
      case 'HIGH':
        return 'bg-orange-500/10 border-orange-500/30 text-orange-400';
      case 'MEDIUM':
        return 'bg-amber-500/10 border-amber-500/30 text-amber-400';
      default:
        return 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400';
    }
  };

  const getPresenceBadge = (status) => {
    switch (status) {
      case 'PRESENT':
        return {
          bg: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
          label: 'Present in Document',
          icon: <CheckCircle2 className="w-3 h-3 text-emerald-400" />,
        };
      case 'ABSENT':
        return {
          bg: 'bg-slate-800 text-slate-400 border-slate-700',
          label: 'Clause Absent',
          icon: <XCircle className="w-3 h-3 text-slate-400" />,
        };
      case 'RETRIEVAL_FAILED_TO_FIND':
        return {
          bg: 'bg-amber-500/10 text-amber-300 border-amber-500/30',
          label: 'Retrieval Incomplete',
          icon: <AlertCircle className="w-3 h-3 text-amber-400" />,
        };
      case 'AMBIGUOUS':
        return {
          bg: 'bg-purple-500/10 text-purple-300 border-purple-500/30',
          label: 'Ambiguous Wording',
          icon: <HelpCircle className="w-3 h-3 text-purple-400" />,
        };
      case 'CONFLICTING':
        return {
          bg: 'bg-rose-500/15 text-rose-300 border-rose-500/30',
          label: 'Conflicting Clauses',
          icon: <AlertCircle className="w-3 h-3 text-rose-400" />,
        };
      default:
        return {
          bg: 'bg-slate-800 text-slate-300 border-slate-700',
          label: status || 'Evaluated',
          icon: <ShieldCheck className="w-3 h-3 text-slate-400" />,
        };
    }
  };

  const handleCopy = (id, text) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <div className="glass-panel rounded-2xl p-6 border border-slate-800 space-y-5">
      {/* Header and Filter Controls */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h3 className="text-base font-semibold text-white flex items-center space-x-2">
            <Scale className="w-5 h-5 text-emerald-400" />
            <span>Clause Risk Evidence & Redline Inspector</span>
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">
            Verified clause citations, policy mismatch evaluations, and targeted counter-proposals
          </p>
        </div>

        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search clauses or category..."
            className="pl-9 pr-4 py-1.5 bg-slate-950 border border-slate-800 focus:border-emerald-500 rounded-lg text-xs text-slate-200 outline-none transition w-full sm:w-60"
          />
        </div>
      </div>

      {/* Filter Row: Review Priority & Presence Status */}
      <div className="flex flex-wrap items-center justify-between gap-3 text-xs">
        {/* Priority Filter */}
        <div className="flex items-center space-x-1.5 overflow-x-auto">
          <span className="text-slate-500 text-[11px] font-medium mr-1">Priority:</span>
          {['ALL', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map((lvl) => (
            <button
              key={lvl}
              onClick={() => setRiskFilter(lvl)}
              className={`px-2.5 py-1 rounded-lg text-xs font-medium transition ${
                riskFilter === lvl
                  ? 'bg-emerald-500 text-slate-950 font-bold shadow-sm shadow-emerald-500/20'
                  : 'bg-slate-900 text-slate-400 hover:text-white border border-slate-800'
              }`}
            >
              {lvl}
            </button>
          ))}
        </div>

        {/* Presence Status Filter */}
        <div className="flex items-center space-x-1.5 overflow-x-auto">
          <span className="text-slate-500 text-[11px] font-medium mr-1">Presence:</span>
          {[
            { id: 'ALL', label: 'All Statuses' },
            { id: 'PRESENT', label: 'Present' },
            { id: 'ABSENT', label: 'Absent' },
            { id: 'RETRIEVAL_FAILED_TO_FIND', label: 'Retrieval Incomplete' },
            { id: 'AMBIGUOUS', label: 'Ambiguous' },
          ].map((st) => (
            <button
              key={st.id}
              onClick={() => setStatusFilter(st.id)}
              className={`px-2.5 py-1 rounded-lg text-[11px] font-medium transition ${
                statusFilter === st.id
                  ? 'bg-slate-700 text-white font-bold'
                  : 'bg-slate-900 text-slate-400 hover:text-slate-300 border border-slate-800'
              }`}
            >
              {st.label}
            </button>
          ))}
        </div>
      </div>

      {/* Filter summary */}
      <div className="text-[11px] text-slate-400 flex items-center space-x-1.5">
        <Filter className="w-3 h-3 text-slate-500" />
        <span>
          Displaying <strong className="text-white">{filteredClauses.length}</strong> of{' '}
          <strong className="text-white">{clauses.length}</strong> audited clauses
        </span>
      </div>

      {/* Clause Cards List */}
      <div className="space-y-4">
        {filteredClauses.map((clause) => {
          const isExpanded = expandedId === clause.id;
          const presence = getPresenceBadge(clause.presence_status);
          const priority = clause.review_priority || clause.risk_level || 'MEDIUM';

          return (
            <div
              key={clause.id}
              className="rounded-xl bg-slate-900/60 border border-slate-800/80 overflow-hidden transition-all hover:border-slate-700"
            >
              {/* Card Header */}
              <div
                onClick={() => setExpandedId(isExpanded ? null : clause.id)}
                className="p-4 cursor-pointer flex items-start justify-between gap-4 select-none"
              >
                <div className="space-y-1.5 min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    {/* Priority badge */}
                    <span
                      className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold border uppercase tracking-wider ${getPriorityStyle(
                        priority
                      )}`}
                    >
                      {priority} Priority
                    </span>

                    {/* Presence status badge */}
                    <span
                      className={`px-2 py-0.5 rounded-md text-[10px] font-medium border flex items-center space-x-1 ${presence.bg}`}
                    >
                      {presence.icon}
                      <span>{presence.label}</span>
                    </span>

                    {/* Category pill */}
                    <span className="text-[11px] text-slate-400 font-medium px-2 py-0.5 rounded bg-slate-800 border border-slate-700/60">
                      {clause.category}
                    </span>

                    {/* Cited Chunk Pill */}
                    {clause.cited_chunk_id && (
                      <span className="font-mono text-[10px] text-emerald-400 px-2 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/20">
                        {clause.cited_chunk_id}
                      </span>
                    )}
                  </div>

                  <h4 className="text-sm font-semibold text-slate-100 pt-0.5">
                    {clause.clause_title}
                  </h4>
                </div>

                <button
                  type="button"
                  className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 mt-1 flex-shrink-0"
                >
                  {isExpanded ? (
                    <ChevronUp className="w-5 h-5" />
                  ) : (
                    <ChevronDown className="w-5 h-5" />
                  )}
                </button>
              </div>

              {/* Card Body */}
              {isExpanded && (
                <div className="px-4 pb-4 space-y-4 pt-2 border-t border-slate-800/60 text-xs">
                  {/* Cited Evidence Excerpt & Jump Button */}
                  <div>
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-slate-400 font-semibold uppercase tracking-wider text-[10px] flex items-center space-x-1.5">
                        <Layers className="w-3.5 h-3.5 text-emerald-400" />
                        <span>Contract Evidence Excerpt:</span>
                      </span>

                      {/* Click citation button to navigate to document viewer */}
                      {clause.cited_chunk_id && (
                        <button
                          type="button"
                          onClick={() =>
                            onSelectCitation &&
                            onSelectCitation({
                              contractId,
                              chunkId: clause.cited_chunk_id,
                            })
                          }
                          className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-lg bg-emerald-500/15 hover:bg-emerald-500/25 text-emerald-300 border border-emerald-500/30 text-[11px] font-semibold transition"
                        >
                          <Target className="w-3 h-3 text-emerald-400" />
                          <span>Focus in Document ({clause.cited_chunk_id})</span>
                        </button>
                      )}
                    </div>

                    <blockquote className="p-3 rounded-lg bg-slate-950 font-mono text-[11px] text-slate-300 leading-relaxed border-l-2 border-emerald-500 selection:bg-emerald-500/30">
                      "{clause.cited_evidence || clause.original_text || 'No text excerpt indexed.'}"
                    </blockquote>
                  </div>

                  {/* Explanation / Risk Analysis */}
                  <div className="p-3 rounded-lg bg-rose-500/5 border border-rose-500/20 text-rose-300 space-y-1">
                    <div className="font-semibold text-rose-400 flex items-center space-x-1.5">
                      <AlertCircle className="w-4 h-4" />
                      <span>Legal Risk Explanation</span>
                    </div>
                    <p className="leading-relaxed text-slate-300 text-xs">
                      {clause.explanation || clause.risk_reasoning}
                    </p>
                  </div>

                  {/* Policy Mismatch (if any) */}
                  {clause.policy_mismatch && (
                    <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-300 space-y-1">
                      <div className="font-semibold text-amber-400 flex items-center space-x-1.5">
                        <Scale className="w-4 h-4" />
                        <span>Review Policy Mismatch</span>
                      </div>
                      <p className="leading-relaxed text-xs">{clause.policy_mismatch}</p>
                    </div>
                  )}

                  {/* Missing Information (if any) */}
                  {clause.missing_information && (
                    <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 text-slate-400 space-y-1">
                      <div className="font-semibold text-slate-300 flex items-center space-x-1.5">
                        <FileQuestion className="w-4 h-4 text-sky-400" />
                        <span>Missing Contract Information</span>
                      </div>
                      <p className="leading-relaxed text-xs">{clause.missing_information}</p>
                    </div>
                  )}

                  {/* Suggested Questions for Human Counsel */}
                  {clause.suggested_questions && clause.suggested_questions.length > 0 && (
                    <div className="p-3 rounded-lg bg-slate-950/80 border border-slate-800 space-y-2">
                      <div className="font-semibold text-indigo-400 flex items-center space-x-1.5">
                        <HelpCircle className="w-4 h-4" />
                        <span>Suggested Questions for Human Counsel</span>
                      </div>
                      <ul className="space-y-1 pl-4 list-disc text-slate-300 text-xs">
                        {clause.suggested_questions.map((q, qIdx) => (
                          <li key={qIdx}>{q}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Suggested Revision (Redline) */}
                  {clause.suggested_revision && (
                    <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-semibold text-teal-400 text-[10px] uppercase tracking-wider">
                          Suggested Balanced Counter-Draft (Redline)
                        </span>
                        <button
                          type="button"
                          onClick={() => handleCopy(clause.id, clause.suggested_revision)}
                          className="flex items-center space-x-1 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 transition text-[11px]"
                        >
                          {copiedId === clause.id ? (
                            <>
                              <Check className="w-3.5 h-3.5 text-emerald-400" />
                              <span className="text-emerald-400 font-medium">Copied</span>
                            </>
                          ) : (
                            <>
                              <Copy className="w-3.5 h-3.5" />
                              <span>Copy Redline</span>
                            </>
                          )}
                        </button>
                      </div>
                      <p className="text-slate-300 font-mono text-[11px] leading-relaxed bg-slate-900/80 p-3 rounded-lg border border-slate-800/80 selection:bg-emerald-500/30">
                        {clause.suggested_revision}
                      </p>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
