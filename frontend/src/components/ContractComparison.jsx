import React, { useState, useEffect } from 'react';
import {
  GitCompare,
  ArrowRightLeft,
  AlertTriangle,
  ShieldCheck,
  CheckCircle,
  HelpCircle,
  FileText,
  Search,
  Sparkles,
  Loader2,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  AlertCircle,
  Scale,
  Layers,
  BookOpen,
} from 'lucide-react';
import { api, SAMPLE_VENDOR_CONTRACT, SAMPLE_BUYER_CONTRACT } from '../services/api';

export default function ContractComparison({
  contracts = [],
  onSelectCitation,
  onContractsUpdated,
}) {
  const [contractAId, setContractAId] = useState('');
  const [contractBId, setContractBId] = useState('');
  const [comparison, setComparison] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [filterLevel, setFilterLevel] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedClauseId, setExpandedClauseId] = useState(null);
  const [loadingDemo, setLoadingDemo] = useState(false);

  // Initialize selected dropdowns when contracts list updates
  useEffect(() => {
    if (contracts.length >= 2) {
      if (!contractAId || !contracts.some((c) => c.contract_id === contractAId)) {
        setContractAId(contracts[0].contract_id);
      }
      if (!contractBId || !contracts.some((c) => c.contract_id === contractBId) || contractBId === contracts[0].contract_id) {
        setContractBId(contracts[1].contract_id);
      }
    } else if (contracts.length === 1) {
      if (!contractAId) setContractAId(contracts[0].contract_id);
    }
  }, [contracts]);

  const handleRunComparison = async (overrideA, overrideB) => {
    const idA = overrideA || contractAId;
    const idB = overrideB || contractBId;

    if (!idA || !idB) {
      setError('Please select two distinct contracts to compare.');
      return;
    }
    if (idA === idB) {
      setError('Please select two different contracts (cannot compare a contract with itself).');
      return;
    }

    setError(null);
    setLoading(true);
    setComparison(null);

    try {
      const data = await api.compareContracts(idA, idB);
      setComparison(data);
      if (data.clauses && data.clauses.length > 0) {
        setExpandedClauseId(data.clauses[0].id);
      }
    } catch (err) {
      setError(err.message || 'Comparison request failed');
    } finally {
      setLoading(false);
    }
  };

  const handleLoadDemoContracts = async () => {
    setLoadingDemo(true);
    setError(null);
    try {
      const [resA, resB] = await Promise.all([
        api.uploadTextContract('Vendor_SaaS_Agreement.txt', SAMPLE_VENDOR_CONTRACT),
        api.uploadTextContract('Buyer_Enterprise_Agreement.txt', SAMPLE_BUYER_CONTRACT),
      ]);
      if (onContractsUpdated) {
        await onContractsUpdated();
      }
      setContractAId(resA.contract_id);
      setContractBId(resB.contract_id);
      await handleRunComparison(resA.contract_id, resB.contract_id);
    } catch (err) {
      setError('Failed to load demo contracts: ' + err.message);
    } finally {
      setLoadingDemo(false);
    }
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case 'PRESENT':
        return (
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
            <CheckCircle className="w-3 h-3" />
            <span>PRESENT</span>
          </span>
        );
      case 'ABSENT':
        return (
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[10px] font-bold bg-slate-800 text-slate-400 border border-slate-700">
            <AlertCircle className="w-3 h-3" />
            <span>ABSENT</span>
          </span>
        );
      case 'RETRIEVAL_FAILED_TO_FIND':
        return (
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/15 text-amber-400 border border-amber-500/30">
            <HelpCircle className="w-3 h-3" />
            <span>RETRIEVAL FAILED</span>
          </span>
        );
      case 'AMBIGUOUS':
        return (
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[10px] font-bold bg-orange-500/15 text-orange-400 border border-orange-500/30">
            <AlertTriangle className="w-3 h-3" />
            <span>AMBIGUOUS</span>
          </span>
        );
      case 'CONFLICTING':
        return (
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[10px] font-bold bg-rose-500/15 text-rose-400 border border-rose-500/30">
            <AlertTriangle className="w-3 h-3" />
            <span>CONFLICTING</span>
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-slate-800 text-slate-400">
            {status}
          </span>
        );
    }
  };

  const getSignificanceBadge = (level) => {
    switch (level) {
      case 'CRITICAL':
        return 'bg-rose-500/15 border-rose-500/30 text-rose-400';
      case 'HIGH':
        return 'bg-orange-500/15 border-orange-500/30 text-orange-400';
      case 'MEDIUM':
        return 'bg-amber-500/15 border-amber-500/30 text-amber-400';
      default:
        return 'bg-emerald-500/15 border-emerald-500/30 text-emerald-400';
    }
  };

  const filteredClauses = (comparison?.clauses || []).filter((clause) => {
    if (filterLevel !== 'ALL' && clause.review_significance !== filterLevel) {
      return false;
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      return (
        clause.category.toLowerCase().includes(q) ||
        clause.clause_title.toLowerCase().includes(q) ||
        clause.difference_summary.toLowerCase().includes(q)
      );
    }
    return true;
  });

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Header & Controls Panel */}
      <div className="glass-panel rounded-2xl p-6 border border-slate-800 shadow-xl space-y-5">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800">
          <div>
            <h2 className="text-base font-semibold text-white flex items-center space-x-2">
              <GitCompare className="w-5 h-5 text-teal-400" />
              <span>Side-by-Side Contract Comparison & Clause Alignment</span>
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Compare termination, liability caps, indemnities, payment, and renewal terms between two agreements using FAISS RAG
            </p>
          </div>

          {/* Quick Demo Mode Button */}
          <button
            onClick={handleLoadDemoContracts}
            disabled={loadingDemo || loading}
            className="inline-flex items-center space-x-2 px-3.5 py-2 rounded-xl bg-gradient-to-r from-teal-600 to-emerald-600 hover:from-teal-500 hover:to-emerald-500 text-white text-xs font-semibold shadow-md shadow-teal-600/20 transition disabled:opacity-50"
          >
            {loadingDemo ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Sparkles className="w-4 h-4 text-teal-200" />
            )}
            <span>Load Demo Comparison (Vendor vs. Buyer)</span>
          </button>
        </div>

        {/* Selection Bar */}
        <div className="grid grid-cols-1 md:grid-cols-12 gap-3 items-center">
          {/* Contract A Dropdown */}
          <div className="md:col-span-5 space-y-1">
            <label className="text-[11px] font-semibold text-slate-300 uppercase tracking-wider block">
              Contract A (Base Agreement):
            </label>
            <select
              value={contractAId}
              onChange={(e) => setContractAId(e.target.value)}
              className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-teal-400"
            >
              <option value="" disabled>
                Select Contract A...
              </option>
              {contracts.map((c) => (
                <option key={c.contract_id} value={c.contract_id}>
                  {c.filename} ({c.total_chunks} chunks)
                </option>
              ))}
            </select>
          </div>

          {/* Switch icon */}
          <div className="md:col-span-2 flex justify-center pt-3 md:pt-4">
            <button
              onClick={() => {
                const temp = contractAId;
                setContractAId(contractBId);
                setContractBId(temp);
              }}
              title="Swap Contracts"
              className="p-2 rounded-xl bg-slate-900 border border-slate-800 text-slate-400 hover:text-white hover:border-slate-700 transition"
            >
              <ArrowRightLeft className="w-4 h-4" />
            </button>
          </div>

          {/* Contract B Dropdown */}
          <div className="md:col-span-5 space-y-1">
            <label className="text-[11px] font-semibold text-slate-300 uppercase tracking-wider block">
              Contract B (Comparison Agreement):
            </label>
            <select
              value={contractBId}
              onChange={(e) => setContractBId(e.target.value)}
              className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-teal-400"
            >
              <option value="" disabled>
                Select Contract B...
              </option>
              {contracts.map((c) => (
                <option key={c.contract_id} value={c.contract_id}>
                  {c.filename} ({c.total_chunks} chunks)
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Action Button */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-2">
          <p className="text-xs text-slate-400">
            {contracts.length < 2
              ? 'Upload at least 2 contracts in the session to run side-by-side comparison.'
              : `${contracts.length} contract(s) available in current session.`}
          </p>

          <button
            onClick={() => handleRunComparison()}
            disabled={loading || !contractAId || !contractBId || contractAId === contractBId}
            className="w-full sm:w-auto inline-flex items-center justify-center space-x-2 px-5 py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs shadow-lg shadow-emerald-500/20 transition disabled:opacity-50"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Comparing Agreements with FAISS...</span>
              </>
            ) : (
              <>
                <GitCompare className="w-4 h-4" />
                <span>Execute Contract Comparison</span>
              </>
            )}
          </button>
        </div>

        {/* Error Notification */}
        {error && (
          <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs flex items-center space-x-2">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}
      </div>

      {/* Loading Skeleton */}
      {loading && (
        <div className="glass-panel rounded-2xl p-12 text-center space-y-4 animate-pulse">
          <Loader2 className="w-10 h-10 animate-spin text-teal-400 mx-auto" />
          <h3 className="text-sm font-semibold text-slate-200">
            Aligning Clauses & Evaluating Structural Differences...
          </h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto">
            Retrieving relevant sections from both vector indexes and validating citations across 8 core categories.
          </p>
        </div>
      )}

      {/* Comparison Results */}
      {comparison && !loading && (
        <div className="space-y-6 animate-slideUp">
          {/* Executive Summary Card */}
          <div className="glass-panel rounded-2xl p-6 border border-slate-800 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center space-x-2">
                <Scale className="w-5 h-5 text-teal-400" />
                <h3 className="text-base font-semibold text-white">Comparative Executive Audit</h3>
              </div>
              <span className="text-xs text-slate-400">
                {comparison.clauses?.length || 0} Categories Evaluated
              </span>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed">
              {comparison.executive_summary}
            </p>

            {/* Key Differences Bullets */}
            {comparison.key_differences && comparison.key_differences.length > 0 && (
              <div className="p-3.5 rounded-xl bg-slate-900/70 border border-slate-800 space-y-2">
                <span className="text-[11px] font-bold text-teal-400 uppercase tracking-wider block">
                  Key Strategic Differences:
                </span>
                <ul className="space-y-1.5 text-xs text-slate-300">
                  {comparison.key_differences.map((diff, idx) => (
                    <li key={idx} className="flex items-start space-x-2">
                      <span className="text-teal-400 font-bold">•</span>
                      <span>{diff}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Neutrality & Legal Disclaimer */}
            <div className="p-3 rounded-xl bg-slate-900/40 border border-slate-800 text-[11px] text-slate-400 flex items-start space-x-2">
              <ShieldCheck className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
              <div>
                <span className="font-semibold text-slate-300">Legal Neutrality Guardrail: </span>
                {comparison.legal_disclaimer}
              </div>
            </div>
          </div>

          {/* Filter & Search Bar */}
          <div className="glass-panel rounded-2xl p-4 border border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-3">
            {/* Search Input */}
            <div className="relative w-full sm:w-64">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search clause category..."
                className="w-full bg-slate-900 border border-slate-700 rounded-xl pl-9 pr-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-teal-400"
              />
            </div>

            {/* Level Filters */}
            <div className="flex items-center space-x-1.5 overflow-x-auto w-full sm:w-auto">
              {['ALL', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map((lvl) => (
                <button
                  key={lvl}
                  onClick={() => setFilterLevel(lvl)}
                  className={`px-3 py-1 rounded-lg text-xs font-semibold transition ${
                    filterLevel === lvl
                      ? 'bg-teal-500 text-slate-950 shadow-sm shadow-teal-500/20'
                      : 'bg-slate-900 text-slate-400 hover:text-white border border-slate-800'
                  }`}
                >
                  {lvl}
                </button>
              ))}
            </div>
          </div>

          {/* Clause Comparison List */}
          <div className="space-y-4">
            {filteredClauses.map((clause) => {
              const isExpanded = expandedClauseId === clause.id;
              return (
                <div
                  key={clause.id}
                  className="glass-panel rounded-2xl border border-slate-800 overflow-hidden transition hover:border-slate-700"
                >
                  {/* Card Header */}
                  <div
                    onClick={() => setExpandedClauseId(isExpanded ? null : clause.id)}
                    className="p-4 cursor-pointer flex flex-wrap items-center justify-between gap-3 bg-slate-900/60 select-none border-b border-slate-800/80"
                  >
                    <div className="flex items-center space-x-3">
                      <span
                        className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold border uppercase ${getSignificanceBadge(
                          clause.review_significance
                        )}`}
                      >
                        {clause.review_significance}
                      </span>
                      <div>
                        <h4 className="text-sm font-semibold text-white">
                          {clause.category}: {clause.clause_title}
                        </h4>
                      </div>
                    </div>

                    <div className="flex items-center space-x-3">
                      <span className="text-xs text-slate-400 hidden sm:inline">
                        {clause.contract_a.presence_status} vs. {clause.contract_b.presence_status}
                      </span>
                      <button className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800">
                        {isExpanded ? (
                          <ChevronUp className="w-4 h-4" />
                        ) : (
                          <ChevronDown className="w-4 h-4" />
                        )}
                      </button>
                    </div>
                  </div>

                  {/* Summary Preview Banner */}
                  <div className="px-4 py-2.5 bg-slate-950/40 text-xs text-slate-300 border-b border-slate-800/60 flex items-start space-x-2">
                    <span className="text-teal-400 font-semibold flex-shrink-0">Difference:</span>
                    <span>{clause.difference_summary}</span>
                  </div>

                  {/* Expanded Body: Side-by-Side Analysis */}
                  {isExpanded && (
                    <div className="p-5 space-y-5 text-xs">
                      {/* Side by Side Columns */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {/* Column A */}
                        <div className="rounded-xl bg-slate-900/80 border border-slate-800 p-4 space-y-3">
                          <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                            <span className="font-bold text-slate-200 truncate max-w-[200px]">
                              {clause.contract_a.filename}
                            </span>
                            {getStatusBadge(clause.contract_a.presence_status)}
                          </div>

                          <div>
                            <span className="text-[10px] uppercase font-bold text-slate-400 block mb-1">
                              Summary of Terms:
                            </span>
                            <p className="text-slate-300 leading-relaxed">
                              {clause.contract_a.summary}
                            </p>
                          </div>

                          {clause.contract_a.cited_evidence && (
                            <div>
                              <span className="text-[10px] uppercase font-bold text-slate-400 block mb-1">
                                Cited Excerpt:
                              </span>
                              <blockquote className="p-2.5 rounded-lg bg-slate-950 text-slate-300 font-mono text-[11px] border-l-2 border-teal-400">
                                "{clause.contract_a.cited_evidence}"
                              </blockquote>
                            </div>
                          )}

                          {clause.contract_a.cited_chunk_id && (
                            <div className="pt-1 flex items-center justify-between text-[11px]">
                              <span className="text-slate-500 font-mono">
                                Chunk: {clause.contract_a.cited_chunk_id}
                                {clause.contract_a.citation?.page_number &&
                                  ` • Page ${clause.contract_a.citation.page_number}`}
                              </span>
                              {onSelectCitation && (
                                <button
                                  onClick={() =>
                                    onSelectCitation({
                                      contractId: clause.contract_a.contract_id,
                                      chunkId: clause.contract_a.cited_chunk_id,
                                      pageNumber: clause.contract_a.citation?.page_number,
                                      filename: clause.contract_a.filename,
                                    })
                                  }
                                  className="inline-flex items-center space-x-1 text-teal-400 hover:text-teal-300 font-semibold"
                                >
                                  <span>View Document Chunk</span>
                                  <ExternalLink className="w-3 h-3" />
                                </button>
                              )}
                            </div>
                          )}
                        </div>

                        {/* Column B */}
                        <div className="rounded-xl bg-slate-900/80 border border-slate-800 p-4 space-y-3">
                          <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                            <span className="font-bold text-slate-200 truncate max-w-[200px]">
                              {clause.contract_b.filename}
                            </span>
                            {getStatusBadge(clause.contract_b.presence_status)}
                          </div>

                          <div>
                            <span className="text-[10px] uppercase font-bold text-slate-400 block mb-1">
                              Summary of Terms:
                            </span>
                            <p className="text-slate-300 leading-relaxed">
                              {clause.contract_b.summary}
                            </p>
                          </div>

                          {clause.contract_b.cited_evidence && (
                            <div>
                              <span className="text-[10px] uppercase font-bold text-slate-400 block mb-1">
                                Cited Excerpt:
                              </span>
                              <blockquote className="p-2.5 rounded-lg bg-slate-950 text-slate-300 font-mono text-[11px] border-l-2 border-emerald-400">
                                "{clause.contract_b.cited_evidence}"
                              </blockquote>
                            </div>
                          )}

                          {clause.contract_b.cited_chunk_id && (
                            <div className="pt-1 flex items-center justify-between text-[11px]">
                              <span className="text-slate-500 font-mono">
                                Chunk: {clause.contract_b.cited_chunk_id}
                                {clause.contract_b.citation?.page_number &&
                                  ` • Page ${clause.contract_b.citation.page_number}`}
                              </span>
                              {onSelectCitation && (
                                <button
                                  onClick={() =>
                                    onSelectCitation({
                                      contractId: clause.contract_b.contract_id,
                                      chunkId: clause.contract_b.cited_chunk_id,
                                      pageNumber: clause.contract_b.citation?.page_number,
                                      filename: clause.contract_b.filename,
                                    })
                                  }
                                  className="inline-flex items-center space-x-1 text-emerald-400 hover:text-emerald-300 font-semibold"
                                >
                                  <span>View Document Chunk</span>
                                  <ExternalLink className="w-3 h-3" />
                                </button>
                              )}
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Human Review Rationale */}
                      <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-2">
                        <span className="text-[11px] font-bold text-amber-400 uppercase tracking-wider block">
                          Why This Difference Warrants Human Review:
                        </span>
                        <p className="text-slate-300 leading-relaxed">
                          {clause.human_review_rationale}
                        </p>

                        {clause.suggested_questions && clause.suggested_questions.length > 0 && (
                          <div className="pt-2 border-t border-slate-800/80">
                            <span className="text-[10px] uppercase font-bold text-slate-400 block mb-1">
                              Targeted Questions for Counsel:
                            </span>
                            <ul className="space-y-1 text-slate-300">
                              {clause.suggested_questions.map((q, qIdx) => (
                                <li key={qIdx} className="flex items-start space-x-1.5">
                                  <span className="text-amber-400 font-bold">•</span>
                                  <span>{q}</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}

            {filteredClauses.length === 0 && (
              <div className="glass-panel rounded-2xl p-8 text-center text-slate-400 text-xs">
                No clauses matched the selected filter criteria.
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
