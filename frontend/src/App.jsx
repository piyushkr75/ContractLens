import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import FileUpload from './components/FileUpload';
import HealthModal from './components/HealthModal';
import RiskOverview from './components/RiskOverview';
import ClauseInspector from './components/ClauseInspector';
import ContractChat from './components/ContractChat';
import DocumentViewer from './components/DocumentViewer';
import RiskReport from './components/RiskReport';
import ContractComparison from './components/ContractComparison';
import { api } from './services/api';
import {
  ShieldAlert,
  MessageSquare,
  FileText,
  Trash2,
  Layers,
  ChevronDown,
  Sparkles,
  Loader2,
  FileBarChart2,
  GitCompare,
  AlertCircle,
  X,
} from 'lucide-react';

export default function App() {
  const [health, setHealth] = useState(null);
  const [isHealthModalOpen, setIsHealthModalOpen] = useState(false);
  const [contracts, setContracts] = useState([]);
  const [selectedContractId, setSelectedContractId] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [contractDetail, setContractDetail] = useState(null);
  const [activeTab, setActiveTab] = useState('risk'); // 'risk' | 'compare' | 'chat' | 'document' | 'report'
  const [loadingAnalysis, setLoadingAnalysis] = useState(false);
  const [globalError, setGlobalError] = useState(null);

  // Citation tracking: when user clicks a citation in Chat, ClauseInspector, or Comparison
  const [activeTargetCitation, setActiveTargetCitation] = useState(null);

  // Health check on mount and interval
  const checkHealth = async () => {
    try {
      const data = await api.getHealth();
      setHealth(data);
    } catch (err) {
      console.warn('Backend not yet reachable:', err.message);
      setHealth({ status: 'offline', in_memory_documents_count: 0, faiss_indexes_count: 0 });
    }
  };

  // Refresh contracts list
  const refreshContracts = async () => {
    try {
      const list = await api.listContracts();
      setContracts(list);
      if (list.length > 0 && !selectedContractId) {
        setSelectedContractId(list[0].contract_id);
      }
    } catch (err) {
      console.warn('Failed to load contracts:', err.message);
    }
  };

  useEffect(() => {
    checkHealth();
    refreshContracts();
    const interval = setInterval(checkHealth, 15000);
    return () => clearInterval(interval);
  }, []);

  // When selected contract changes, fetch its analysis and detail
  useEffect(() => {
    if (!selectedContractId) {
      setAnalysis(null);
      setContractDetail(null);
      return;
    }

    const loadContractData = async () => {
      setLoadingAnalysis(true);
      setGlobalError(null);
      try {
        const [detailData, analysisData] = await Promise.all([
          api.getContract(selectedContractId),
          api.analyzeContract(selectedContractId),
        ]);
        setContractDetail(detailData);
        setAnalysis(analysisData);
        checkHealth();
      } catch (err) {
        console.error('Error loading contract data:', err);
        setGlobalError(`Failed to load contract intelligence: ${err.message}`);
      } finally {
        setLoadingAnalysis(false);
      }
    };

    loadContractData();
  }, [selectedContractId]);

  const handleUploadSuccess = async (newContractId) => {
    await refreshContracts();
    setSelectedContractId(newContractId);
    checkHealth();
  };

  const handleCompareReady = async (idA, idB) => {
    await refreshContracts();
    setSelectedContractId(idA);
    setActiveTab('compare');
    checkHealth();
  };

  const handleReAnalyze = async (policyText) => {
    if (!selectedContractId) return;
    setLoadingAnalysis(true);
    setGlobalError(null);
    try {
      const analysisData = await api.analyzeContract(selectedContractId, policyText);
      setAnalysis(analysisData);
      await refreshContracts();
    } catch (err) {
      setGlobalError(`Re-analysis failed: ${err.message}`);
    } finally {
      setLoadingAnalysis(false);
    }
  };

  const handleDeleteContract = async (id, e) => {
    e.stopPropagation();
    if (!confirm('Remove this contract and its in-memory FAISS index?')) return;
    try {
      await api.deleteContract(id);
      const remaining = contracts.filter((c) => c.contract_id !== id);
      setContracts(remaining);
      if (selectedContractId === id) {
        setSelectedContractId(remaining.length > 0 ? remaining[0].contract_id : null);
      }
      checkHealth();
    } catch (err) {
      alert('Failed to delete contract: ' + err.message);
    }
  };

  // Navigating directly to cited chunk/page
  const handleSelectCitation = (citation) => {
    if (!citation) return;
    if (citation.contractId && citation.contractId !== selectedContractId) {
      setSelectedContractId(citation.contractId);
    }
    setActiveTargetCitation(citation);
    setActiveTab('document');
  };

  const selectedContractMeta = contracts.find((c) => c.contract_id === selectedContractId);

  const tabs = [
    { id: 'risk', label: 'Risk Intelligence', icon: <ShieldAlert className="w-4 h-4" /> },
    { id: 'compare', label: 'Contract Comparison', icon: <GitCompare className="w-4 h-4" /> },
    { id: 'chat', label: 'FAISS RAG Assistant', icon: <MessageSquare className="w-4 h-4" /> },
    { id: 'document', label: 'Document & Chunks', icon: <FileText className="w-4 h-4" /> },
    { id: 'report', label: 'Export Report', icon: <FileBarChart2 className="w-4 h-4" /> },
  ];

  return (
    <div className="min-h-screen bg-[#080c14] text-slate-100 flex flex-col font-sans selection:bg-emerald-500/30 selection:text-white">
      <Navbar
        health={health}
        onRefreshHealth={checkHealth}
        onOpenHealthModal={() => setIsHealthModalOpen(true)}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Global Error Banner */}
        {globalError && (
          <div className="p-4 rounded-2xl bg-rose-500/10 border border-rose-500/30 flex items-center justify-between text-xs text-rose-300 animate-slideDown shadow-lg shadow-rose-500/10">
            <div className="flex items-center space-x-2.5">
              <AlertCircle className="w-5 h-5 text-rose-400 flex-shrink-0" />
              <span>{globalError}</span>
            </div>
            <button
              onClick={() => setGlobalError(null)}
              className="p-1 rounded-lg hover:bg-rose-500/20 text-rose-400"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Hero Section */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 animate-fadeIn">
          <div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
              Enterprise{' '}
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 to-teal-300">
                Contract Risk Intelligence
              </span>
            </h1>
            <p className="text-xs sm:text-sm text-slate-400 mt-1 max-w-2xl leading-relaxed">
              Automated commercial agreement auditing with in-memory FAISS RAG, verified citation
              evidence, clause comparison, and real-time external legal cross-examination.
            </p>
          </div>
        </div>

        {/* Ingest / File Upload Section */}
        <FileUpload
          onUploadSuccess={handleUploadSuccess}
          onCompareReady={handleCompareReady}
        />

        {/* Active Contracts Switcher Bar */}
        {contracts.length > 0 && (
          <div className="glass-panel rounded-2xl p-4 border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-4 animate-slideUp">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-400 mr-1">
                Active Contracts:
              </span>
              <div className="flex flex-wrap gap-2">
                {contracts.map((c) => (
                  <button
                    key={c.contract_id}
                    onClick={() => setSelectedContractId(c.contract_id)}
                    className={`flex items-center space-x-2 px-3 py-1.5 rounded-xl text-xs font-medium transition-all duration-200 ${
                      selectedContractId === c.contract_id
                        ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/50 shadow-sm shadow-emerald-500/20 font-bold scale-[1.02]'
                        : 'bg-slate-900 text-slate-400 hover:text-white border border-slate-800 hover:border-slate-700'
                    }`}
                  >
                    <span className="truncate max-w-[170px]">{c.filename}</span>
                    {c.overall_risk_level && (
                      <span
                        className={`text-[9px] font-bold px-1.5 py-0.5 rounded ${
                          c.overall_risk_level === 'CRITICAL'
                            ? 'bg-rose-500/20 text-rose-400'
                            : c.overall_risk_level === 'HIGH'
                            ? 'bg-orange-500/20 text-orange-400'
                            : c.overall_risk_level === 'MEDIUM'
                            ? 'bg-amber-500/20 text-amber-400'
                            : 'bg-emerald-500/20 text-emerald-400'
                        }`}
                      >
                        {c.overall_risk_level}
                      </span>
                    )}
                    <span
                      onClick={(e) => handleDeleteContract(c.contract_id, e)}
                      title="Remove from in-memory session"
                      className="text-slate-500 hover:text-rose-400 p-0.5 rounded transition"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </span>
                  </button>
                ))}
              </div>
            </div>

            {selectedContractMeta && (
              <div className="text-xs text-slate-400 flex items-center space-x-3 flex-shrink-0">
                <span>{(selectedContractMeta.file_size_bytes / 1024).toFixed(1)} KB</span>
                <span>•</span>
                <span>{selectedContractMeta.total_chunks} FAISS Chunks</span>
                {selectedContractMeta.overall_risk_score != null && (
                  <>
                    <span>•</span>
                    <span className="font-semibold text-emerald-400">
                      Risk: {selectedContractMeta.overall_risk_score}/100
                    </span>
                  </>
                )}
              </div>
            )}
          </div>
        )}

        {/* Content Tabs Navigation */}
        <div className="space-y-6">
          <div className="flex items-center space-x-2 border-b border-slate-800 pb-3 overflow-x-auto">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center space-x-2 px-4 py-2 rounded-xl text-xs font-semibold transition-all duration-200 whitespace-nowrap ${
                  activeTab === tab.id
                    ? 'bg-emerald-500 text-slate-950 shadow-md shadow-emerald-500/20 font-bold scale-[1.02]'
                    : 'bg-slate-900 text-slate-400 hover:text-white border border-slate-800 hover:border-slate-700'
                }`}
              >
                {tab.icon}
                <span>{tab.label}</span>
              </button>
            ))}
          </div>

          {/* Tab 1: Contract Comparison (Accessible even if single contract is active, with prompt or demo trigger) */}
          {activeTab === 'compare' && (
            <div className="animate-slideUp">
              <ContractComparison
                contracts={contracts}
                onSelectCitation={handleSelectCitation}
                onContractsUpdated={refreshContracts}
              />
            </div>
          )}

          {/* Active Contract Views */}
          {activeTab !== 'compare' && (
            <>
              {selectedContractId ? (
                <>
                  {loadingAnalysis ? (
                    <div className="glass-panel rounded-2xl p-12 text-center space-y-3 animate-pulse border border-slate-800">
                      <Loader2 className="w-8 h-8 animate-spin text-emerald-400 mx-auto" />
                      <p className="text-sm font-medium text-slate-200">
                        Auditing Contract Clauses Against Commercial Baseline...
                      </p>
                      <p className="text-xs text-slate-400">
                        Evaluating indemnification, aggregate liability, termination penalties, and renewal barriers
                      </p>
                    </div>
                  ) : (
                    <>
                      {/* Risk Intelligence Tab */}
                      {activeTab === 'risk' && analysis && (
                        <div className="space-y-6 animate-slideUp">
                          <RiskOverview analysis={analysis} />
                          <ClauseInspector
                            clauses={analysis.clauses}
                            contractId={selectedContractId}
                            onSelectCitation={handleSelectCitation}
                          />
                        </div>
                      )}

                      {/* Chat Tab */}
                      {activeTab === 'chat' && (
                        <div className="animate-slideUp">
                          <ContractChat
                            contractId={selectedContractId}
                            filename={selectedContractMeta?.filename || 'Active Contract'}
                            onSelectCitation={handleSelectCitation}
                          />
                        </div>
                      )}

                      {/* Document Viewer & Chunk Inspector Tab */}
                      {activeTab === 'document' && (
                        <div className="animate-slideUp">
                          <DocumentViewer
                            contractDetail={contractDetail}
                            contractId={selectedContractId}
                            activeTargetCitation={activeTargetCitation}
                            onClearActiveTarget={() => setActiveTargetCitation(null)}
                          />
                        </div>
                      )}

                      {/* Exportable Report Tab */}
                      {activeTab === 'report' && analysis && (
                        <div className="animate-slideUp">
                          <RiskReport
                            analysis={analysis}
                            filename={selectedContractMeta?.filename || 'Contract'}
                            contractId={selectedContractId}
                            onSelectCitation={handleSelectCitation}
                            onReAnalyze={handleReAnalyze}
                            loadingAnalysis={loadingAnalysis}
                          />
                        </div>
                      )}
                    </>
                  )}
                </>
              ) : (
                /* Empty state when no contract is loaded yet */
                <div className="glass-panel rounded-2xl p-12 text-center border border-slate-800/80 space-y-4 animate-fadeIn">
                  <div className="w-16 h-16 rounded-2xl bg-slate-900 border border-slate-800 text-emerald-400 flex items-center justify-center mx-auto shadow-inner">
                    <ShieldAlert className="w-8 h-8" />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-white">No Agreement Loaded</h3>
                    <p className="text-xs text-slate-400 max-w-md mx-auto mt-1 leading-relaxed">
                      Upload an agreement above, or click{' '}
                      <span className="text-emerald-400 font-semibold">Demo: Enterprise MSA</span> to
                      instantly populate the in-memory FAISS index and inspect clause risk.
                    </p>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800/60 py-6 text-center text-xs text-slate-500 bg-[#090d16]">
        ContractLens™ • In-Memory FAISS Vector Engine • Verified Legal Citations
      </footer>

      {/* Health Inspection Modal */}
      {isHealthModalOpen && (
        <HealthModal health={health} onClose={() => setIsHealthModalOpen(false)} />
      )}
    </div>
  );
}
