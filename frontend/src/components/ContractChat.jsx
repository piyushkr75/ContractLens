import React, { useState, useRef, useEffect } from 'react';
import {
  Send,
  Bot,
  User,
  Sparkles,
  BookOpen,
  Loader2,
  ChevronRight,
  ChevronDown,
  Globe,
  ExternalLink,
  Shield,
  AlertTriangle,
  Scale,
  FileText,
  Info,
  Target,
  ArrowRight,
} from 'lucide-react';
import { api } from '../services/api';

export default function ContractChat({ contractId, filename, onSelectCitation }) {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: `Hello! I am your ContractLens legal assistant. I have indexed **${filename}** into the in-memory FAISS vector store.\n\nYou can ask about clauses, liability caps, termination rights, or enable **MCP External Legal Research** to cross-examine clauses against real-time statutes and enforceability precedents.`,
      citations: [],
      external_sources: [],
      external_research_used: false,
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [researchMode, setResearchMode] = useState('auto'); // 'auto' | 'external_research' | 'document_only'
  const [expandedCitations, setExpandedCitations] = useState({});
  const [expandedSources, setExpandedSources] = useState({});
  const [mcpStatus, setMcpStatus] = useState(null);
  const messagesEndRef = useRef(null);

  // Poll MCP status on mount
  useEffect(() => {
    const fetchMcp = async () => {
      try {
        const data = await api.getMcpStatus();
        setMcpStatus(data);
      } catch (e) {
        setMcpStatus({ enabled: false, connected: false });
      }
    };
    fetchMcp();
  }, []);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const handleSend = async (messageText) => {
    const query = messageText || input;
    if (!query.trim() || loading) return;

    setInput('');
    const userMessage = { role: 'user', content: query };
    setMessages((prev) => [...prev, userMessage]);
    setLoading(true);

    try {
      const historyPayload = messages.map((m) => ({
        role: m.role,
        content: m.content,
      }));

      const res = await api.chatWithContract(
        contractId,
        query,
        historyPayload,
        4,
        researchMode
      );

      // Check for insufficient evidence flags
      const isInsufficient =
        res.evidence_status === 'INSUFFICIENT' ||
        res.evidence_status === 'PARTIAL' ||
        (res.citations && res.citations.length === 0 && researchMode !== 'external_research') ||
        res.response?.toLowerCase().includes('insufficient evidence') ||
        res.response?.toLowerCase().includes('no direct clause');

      const newIdx = messages.length + 1;

      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: res.response,
          citations: res.citations || [],
          research_mode: res.research_mode || researchMode,
          external_research_used: res.external_research_used,
          external_search_status: res.external_search_status,
          external_sources: res.external_sources || [],
          contract_findings: res.contract_findings,
          external_findings: res.external_findings,
          legal_implications: res.legal_implications,
          uncertainties_and_advice: res.uncertainties_and_advice,
          is_insufficient: isInsufficient,
        },
      ]);

      // Automatically expand citations if present
      if (res.citations && res.citations.length > 0) {
        setExpandedCitations((prev) => ({ ...prev, [newIdx]: true }));
      }
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `API Error: ${err.message || 'Failed to communicate with RAG service.'}`,
          citations: [],
          external_sources: [],
          is_error: true,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const sampleQuestions = [
    'Is aggregate liability capped or uncapped in this contract?',
    'What are the notice requirements for termination for cause?',
    'Is this ₹2 lakh employment bond enforceable in India under Section 27?',
    'Does the indemnity cover indirect and consequential damages?',
  ];

  const toggleCitation = (msgIdx) => {
    setExpandedCitations((prev) => ({
      ...prev,
      [msgIdx]: !prev[msgIdx],
    }));
  };

  const toggleSources = (msgIdx) => {
    setExpandedSources((prev) => ({
      ...prev,
      [msgIdx]: !prev[msgIdx],
    }));
  };

  return (
    <div className="glass-panel rounded-2xl border border-slate-800 flex flex-col h-[720px] shadow-2xl overflow-hidden">
      {/* Chat Header */}
      <div className="p-4 border-b border-slate-800 bg-slate-900/80 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center space-x-2.5">
          <div className="w-8 h-8 rounded-lg bg-emerald-500/20 text-emerald-400 flex items-center justify-center">
            <Bot className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-white">Contract RAG & Legal Research</h3>
            <p className="text-[11px] text-slate-400">
              FAISS In-Memory Vectors • Verified Grounded Citations • MCP Web-Search Bridge
            </p>
          </div>
        </div>

        {/* MCP Connection Indicator & Research Mode Selector */}
        <div className="flex items-center space-x-2">
          {mcpStatus?.enabled && (
            <div
              className={`flex items-center space-x-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium border ${
                mcpStatus.connected
                  ? 'bg-indigo-500/10 border-indigo-500/30 text-indigo-300'
                  : 'bg-amber-500/10 border-amber-500/30 text-amber-300'
              }`}
            >
              <Globe className="w-3 h-3" />
              <span>
                MCP Web Search: {mcpStatus.connected ? 'Active' : 'Offline'}
              </span>
            </div>
          )}

          <div className="flex items-center bg-slate-950 p-1 rounded-xl border border-slate-800 text-[11px]">
            <button
              onClick={() => setResearchMode('auto')}
              className={`px-2.5 py-1 rounded-lg transition font-medium ${
                researchMode === 'auto'
                  ? 'bg-emerald-500 text-slate-950 font-bold shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Auto
            </button>
            <button
              onClick={() => setResearchMode('external_research')}
              className={`px-2.5 py-1 rounded-lg transition font-medium ${
                researchMode === 'external_research'
                  ? 'bg-indigo-500 text-white font-bold shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Legal MCP
            </button>
            <button
              onClick={() => setResearchMode('document_only')}
              className={`px-2.5 py-1 rounded-lg transition font-medium ${
                researchMode === 'document_only'
                  ? 'bg-emerald-500 text-slate-950 font-bold shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Doc Only
            </button>
          </div>
        </div>
      </div>

      {/* Suggested Questions Pills */}
      <div className="px-4 py-2 bg-slate-950/60 border-b border-slate-800/80 flex items-center space-x-2 overflow-x-auto text-[11px]">
        <Sparkles className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" />
        <span className="text-slate-500 whitespace-nowrap">Suggested:</span>
        {sampleQuestions.map((sq, idx) => (
          <button
            key={idx}
            disabled={loading}
            onClick={() => handleSend(sq)}
            className="px-2.5 py-1 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 hover:border-slate-700 whitespace-nowrap transition disabled:opacity-50 text-[11px]"
          >
            {sq}
          </button>
        ))}
      </div>

      {/* Message Stream */}
      <div className="flex-1 p-4 overflow-y-auto space-y-4">
        {messages.map((msg, idx) => {
          const isUser = msg.role === 'user';
          const hasExternal = msg.external_sources && msg.external_sources.length > 0;
          const isUnavailable = msg.external_search_status === 'unavailable';
          const isFailed = msg.external_search_status === 'failed';

          return (
            <div
              key={idx}
              className={`flex items-start space-x-3 ${isUser ? 'justify-end' : 'justify-start'}`}
            >
              {!isUser && (
                <div className="w-7 h-7 rounded-lg bg-emerald-500/20 text-emerald-400 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <Bot className="w-4 h-4" />
                </div>
              )}

              <div
                className={`max-w-[85%] rounded-2xl p-4 text-xs leading-relaxed space-y-3 ${
                  isUser
                    ? 'bg-emerald-600 text-white rounded-tr-none'
                    : 'bg-slate-900/90 border border-slate-800 text-slate-200 rounded-tl-none shadow-md'
                }`}
              >
                {/* Insufficient Evidence Warning Banner */}
                {!isUser && msg.is_insufficient && (
                  <div className="p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-300 text-[11px] flex items-start space-x-2">
                    <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
                    <div>
                      <span className="font-semibold text-amber-200">
                        Insufficient Evidence Notice:
                      </span>{' '}
                      The agreement does not provide conclusive contractual text for this query,
                      or terms are not explicitly defined. Human legal review recommended.
                    </div>
                  </div>
                )}

                {/* Notice banner if external search was unavailable or failed */}
                {!isUser && (isUnavailable || isFailed) && (
                  <div className="p-2 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-300 text-[11px] flex items-center space-x-2">
                    <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0" />
                    <span>
                      {isUnavailable
                        ? 'External MCP legal search was unavailable. Answer grounded solely in contract evidence.'
                        : 'External research encountered a tool failure. Answer grounded in contract evidence.'}
                    </span>
                  </div>
                )}

                {/* Structured Breakdown or Plain Content */}
                {!isUser && (msg.contract_findings || msg.external_findings) ? (
                  <div className="space-y-3">
                    {/* Contract Findings */}
                    {msg.contract_findings && (
                      <div className="p-3 rounded-xl bg-slate-950/70 border border-slate-800 space-y-1">
                        <div className="flex items-center space-x-1.5 text-emerald-400 font-semibold text-[11px]">
                          <FileText className="w-3.5 h-3.5" />
                          <span>Uploaded Contract Findings</span>
                        </div>
                        <p className="text-slate-300 whitespace-pre-wrap">{msg.contract_findings}</p>
                      </div>
                    )}

                    {/* External Legal Findings */}
                    {msg.external_findings && (
                      <div className="p-3 rounded-xl bg-indigo-950/30 border border-indigo-900/50 space-y-1">
                        <div className="flex items-center space-x-1.5 text-indigo-400 font-semibold text-[11px]">
                          <Scale className="w-3.5 h-3.5" />
                          <span>External Legal Principles & Precedents (MCP Research)</span>
                        </div>
                        <p className="text-slate-300 whitespace-pre-wrap">{msg.external_findings}</p>
                      </div>
                    )}

                    {/* Legal Implications */}
                    {msg.legal_implications && (
                      <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-1">
                        <div className="flex items-center space-x-1.5 text-amber-400 font-semibold text-[11px]">
                          <Shield className="w-3.5 h-3.5" />
                          <span>Enforceability & Practical Implications</span>
                        </div>
                        <p className="text-slate-300 whitespace-pre-wrap">{msg.legal_implications}</p>
                      </div>
                    )}

                    {/* Uncertainties & Disclaimer */}
                    {msg.uncertainties_and_advice && (
                      <div className="p-2.5 rounded-xl bg-slate-900 border border-slate-800 text-[11px] text-slate-400 space-y-1">
                        <div className="flex items-center space-x-1 font-medium text-slate-300">
                          <Info className="w-3.5 h-3.5 text-slate-400" />
                          <span>Uncertainties & Legal Notice</span>
                        </div>
                        <p className="italic">{msg.uncertainties_and_advice}</p>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="whitespace-pre-wrap">{msg.content}</div>
                )}

                {/* External MCP Sources Accordion */}
                {!isUser && hasExternal && (
                  <div className="pt-2 border-t border-slate-800 text-[11px]">
                    <button
                      type="button"
                      onClick={() => toggleSources(idx)}
                      className="flex items-center space-x-1.5 text-indigo-400 hover:text-indigo-300 font-medium transition"
                    >
                      <Globe className="w-3.5 h-3.5" />
                      <span>{msg.external_sources.length} Verified External Legal Sources (MCP)</span>
                      {expandedSources[idx] ? (
                        <ChevronDown className="w-3 h-3" />
                      ) : (
                        <ChevronRight className="w-3 h-3" />
                      )}
                    </button>

                    {expandedSources[idx] && (
                      <div className="mt-2 space-y-2">
                        {msg.external_sources.map((src, sIdx) => (
                          <div
                            key={sIdx}
                            className="p-2.5 rounded-lg bg-slate-950/90 border border-indigo-900/40 text-[10px] space-y-1"
                          >
                            <div className="flex items-center justify-between gap-2">
                              <a
                                href={src.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="font-semibold text-indigo-300 hover:text-indigo-200 flex items-center space-x-1 truncate max-w-[80%]"
                              >
                                <span className="truncate">{src.title}</span>
                                <ExternalLink className="w-3 h-3 flex-shrink-0" />
                              </a>
                              {src.source_type && (
                                <span className="text-[9px] px-1.5 py-0.5 rounded bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 whitespace-nowrap">
                                  {src.source_type}
                                </span>
                              )}
                            </div>
                            {src.snippet && (
                              <p className="text-slate-400 line-clamp-2 italic">"{src.snippet}"</p>
                            )}
                            <div className="text-[9px] text-slate-500 font-mono flex items-center space-x-2">
                              <span className="truncate">{src.url}</span>
                              {src.publication_date && <span>• {src.publication_date}</span>}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {/* In-Memory FAISS Contract Citations */}
                {!isUser && msg.citations && msg.citations.length > 0 && (
                  <div className="pt-2 border-t border-slate-800 text-[11px]">
                    <button
                      type="button"
                      onClick={() => toggleCitation(idx)}
                      className="flex items-center space-x-1.5 text-emerald-400 hover:text-emerald-300 font-medium transition"
                    >
                      <BookOpen className="w-3.5 h-3.5" />
                      <span>{msg.citations.length} Grounded Contract Citations (FAISS)</span>
                      {expandedCitations[idx] ? (
                        <ChevronDown className="w-3 h-3" />
                      ) : (
                        <ChevronRight className="w-3 h-3" />
                      )}
                    </button>

                    {expandedCitations[idx] && (
                      <div className="mt-2 space-y-2">
                        {msg.citations.map((cite, cIdx) => (
                          <div
                            key={cIdx}
                            className="p-2.5 rounded-lg bg-slate-950/80 border border-slate-800/80 text-[10px] space-y-1.5"
                          >
                            <div className="flex items-center justify-between text-slate-400">
                              <span className="font-semibold text-slate-300">
                                {cite.section_title || `Chunk #${(cite.chunk_index ?? 0) + 1}`}
                                {cite.page_number && ` (Page ${cite.page_number})`}
                              </span>
                              <span className="font-mono text-emerald-400">
                                Match: {((cite.similarity_score ?? 0.85) * 100).toFixed(0)}%
                              </span>
                            </div>
                            <p className="text-slate-400 italic">"{cite.snippet}"</p>

                            {/* Click to open document preview and navigate to cited chunk */}
                            <div className="pt-1 flex items-center justify-between">
                              <span className="font-mono text-[9px] text-slate-500">
                                {cite.chunk_id || `chunk_${cite.chunk_index}`}
                              </span>
                              <button
                                type="button"
                                onClick={() =>
                                  onSelectCitation &&
                                  onSelectCitation({
                                    contractId,
                                    chunkId: cite.chunk_id,
                                    pageNumber: cite.page_number,
                                    filename,
                                  })
                                }
                                className="inline-flex items-center space-x-1 px-2 py-0.5 rounded bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 text-[10px] font-semibold transition"
                              >
                                <Target className="w-3 h-3" />
                                <span>
                                  View in Document
                                  {cite.page_number ? ` (Page ${cite.page_number})` : ''}
                                </span>
                                <ArrowRight className="w-3 h-3" />
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>

              {isUser && (
                <div className="w-7 h-7 rounded-lg bg-slate-800 text-slate-300 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <User className="w-4 h-4" />
                </div>
              )}
            </div>
          );
        })}

        {loading && (
          <div className="flex items-center space-x-2 text-slate-400 text-xs py-2 animate-pulse">
            <Loader2 className="w-4 h-4 animate-spin text-emerald-400" />
            <span>
              {researchMode === 'external_research'
                ? 'Querying MCP search tools & synthesizing external legal precedents...'
                : 'Searching in-memory FAISS vector index & evaluating legal risk...'}
            </span>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Form */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleSend();
        }}
        className="p-3 bg-slate-900/80 border-t border-slate-800 flex items-center space-x-2"
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={
            researchMode === 'external_research'
              ? 'Ask an external enforceability question (e.g. Is this ₹2 lakh employment bond enforceable in India?)...'
              : 'Ask a question about this contract (e.g. Is aggregate liability capped?)...'
          }
          className="flex-1 bg-slate-950 border border-slate-800 focus:border-emerald-500 rounded-xl px-4 py-2.5 text-xs text-slate-200 outline-none transition"
        />
        <button
          type="submit"
          disabled={!input.trim() || loading}
          className="px-4 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold flex items-center space-x-1.5 transition disabled:opacity-50 shadow-md shadow-emerald-600/20"
        >
          <Send className="w-3.5 h-3.5" />
          <span>Send</span>
        </button>
      </form>
    </div>
  );
}
