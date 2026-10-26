import React, { useState, useMemo, useEffect, useRef } from 'react';
import {
  FileText,
  Layers,
  Search,
  Hash,
  BookOpen,
  ChevronDown,
  ChevronUp,
  Copy,
  Check,
  Eye,
  Filter,
  Download,
  ExternalLink,
  Target,
  X,
  FileCode,
} from 'lucide-react';
import { api } from '../services/api';

export default function DocumentViewer({
  contractDetail,
  contractId,
  activeTargetCitation,
  onClearActiveTarget,
}) {
  const [viewMode, setViewMode] = useState('chunks'); // 'text' | 'chunks'
  const [realChunks, setRealChunks] = useState(null);
  const [loadingChunks, setLoadingChunks] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [pageFilter, setPageFilter] = useState('ALL');
  const [expandedChunkIdx, setExpandedChunkIdx] = useState(null);
  const [copiedChunkId, setCopiedChunkId] = useState(null);

  const targetedRef = useRef(null);

  // Fetch true vector-indexed chunks from backend
  useEffect(() => {
    if (!contractId) return;

    let isMounted = true;
    setLoadingChunks(true);

    api
      .getContractChunks(contractId)
      .then((data) => {
        if (isMounted) {
          setRealChunks(data);
          setLoadingChunks(false);
        }
      })
      .catch((err) => {
        console.warn('Could not fetch vector chunks, falling back to client-preview:', err);
        if (isMounted) setLoadingChunks(false);
      });

    return () => {
      isMounted = false;
    };
  }, [contractId]);

  // When activeTargetCitation arrives, switch to 'chunks' view and expand the targeted chunk
  useEffect(() => {
    if (activeTargetCitation && activeTargetCitation.contractId === contractId) {
      setViewMode('chunks');
      // Find chunk index
      if (activeTargetCitation.chunkId && realChunks) {
        const found = realChunks.find((c) => c.chunk_id === activeTargetCitation.chunkId);
        if (found) {
          setExpandedChunkIdx(found.chunk_index);
        }
      }
      setTimeout(() => {
        targetedRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }, 250);
    }
  }, [activeTargetCitation, contractId, realChunks]);

  const handleCopy = (chunkId, text) => {
    navigator.clipboard.writeText(text);
    setCopiedChunkId(chunkId);
    setTimeout(() => setCopiedChunkId(null), 2000);
  };

  // Synthetic chunk fallback from text preview if endpoint is offline
  const fallbackChunks = useMemo(() => {
    if (!contractDetail?.raw_text_preview) return [];
    const text = contractDetail.raw_text_preview;
    const chunkSize = 800;
    const overlap = 100;
    const result = [];
    let idx = 0;
    let pos = 0;

    while (pos < text.length) {
      const end = Math.min(pos + chunkSize, text.length);
      const chunkText = text.slice(pos, end);

      const headingMatch = chunkText.match(/^(?:ARTICLE|SECTION|CLAUSE)\s+\d+[.:]\s*(.+)/im);
      const sectionTitle = headingMatch ? headingMatch[0].trim() : null;

      result.push({
        chunk_id: `chunk_${idx}`,
        chunk_index: idx,
        text: chunkText,
        char_count: chunkText.length,
        word_count: chunkText.split(/\s+/).filter(Boolean).length,
        page_number: Math.floor(idx / 3) + 1,
        section_title: sectionTitle || `Section ${idx + 1}`,
      });

      pos += chunkSize - overlap;
      idx++;
    }

    return result;
  }, [contractDetail?.raw_text_preview]);

  const effectiveChunks = useMemo(() => {
    if (realChunks && realChunks.length > 0) {
      return realChunks.map((c, i) => ({
        ...c,
        word_count: c.text ? c.text.split(/\s+/).filter(Boolean).length : 0,
        char_count: c.text ? c.text.length : 0,
        section_title:
          c.section_title ||
          (c.text?.match(/^(?:ARTICLE|SECTION|CLAUSE)\s+\d+[.:]\s*([^\n\r]+)/im)?.[0] ??
            `Section Chunk #${i + 1}`),
      }));
    }
    return fallbackChunks;
  }, [realChunks, fallbackChunks]);

  // Unique page list for page navigation
  const availablePages = useMemo(() => {
    const pages = new Set();
    effectiveChunks.forEach((c) => {
      if (c.page_number) pages.add(c.page_number);
    });
    return Array.from(pages).sort((a, b) => a - b);
  }, [effectiveChunks]);

  const filteredChunks = useMemo(() => {
    let result = effectiveChunks;

    if (pageFilter !== 'ALL') {
      const pageNum = parseInt(pageFilter, 10);
      result = result.filter((c) => c.page_number === pageNum);
    }

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      result = result.filter(
        (c) =>
          c.text.toLowerCase().includes(q) ||
          (c.section_title && c.section_title.toLowerCase().includes(q)) ||
          c.chunk_id?.toLowerCase().includes(q)
      );
    }

    return result;
  }, [effectiveChunks, pageFilter, searchQuery]);

  if (!contractDetail) return null;

  const totalWords = effectiveChunks.reduce((acc, c) => acc + (c.word_count || 0), 0);
  const totalChars = contractDetail.raw_text_preview?.length || 0;
  const isTargetActive =
    activeTargetCitation && activeTargetCitation.contractId === contractId;

  return (
    <div className="space-y-6">
      {/* Active Targeted Citation Alert Banner */}
      {isTargetActive && (
        <div className="p-4 rounded-2xl bg-emerald-500/10 border-2 border-emerald-500/40 flex items-center justify-between text-xs text-emerald-300 animate-slideDown shadow-lg shadow-emerald-500/10">
          <div className="flex items-center space-x-2.5">
            <Target className="w-5 h-5 text-emerald-400 animate-pulse flex-shrink-0" />
            <div>
              <span className="font-semibold text-white">
                Focused from Citation Link:
              </span>{' '}
              Targeting Chunk{' '}
              <span className="font-mono text-emerald-400 font-bold">
                {activeTargetCitation.chunkId || 'N/A'}
              </span>
              {activeTargetCitation.pageNumber && (
                <span> (Cited on Page {activeTargetCitation.pageNumber})</span>
              )}
            </div>
          </div>
          {onClearActiveTarget && (
            <button
              onClick={onClearActiveTarget}
              className="flex items-center space-x-1 px-2.5 py-1 rounded-lg bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-200 transition text-[11px]"
            >
              <X className="w-3.5 h-3.5" />
              <span>Dismiss Target</span>
            </button>
          )}
        </div>
      )}

      {/* Document Metadata Header */}
      <div className="glass-panel rounded-2xl p-6 border border-slate-800">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
          <div>
            <h3 className="text-base font-semibold text-white flex items-center space-x-2">
              <FileText className="w-5 h-5 text-emerald-400" />
              <span>Document Intelligence & In-Memory Chunk Explorer</span>
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Inspect original ingested text, verify vector-indexed chunks, and navigate cited clauses
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {/* Download Original File Button */}
            <a
              href={api.getContractDownloadUrl(contractId)}
              target="_blank"
              rel="noopener noreferrer"
              download
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 hover:border-slate-700 transition"
              title="Download or preview uploaded file"
            >
              <Download className="w-3.5 h-3.5 text-emerald-400" />
              <span>Download File</span>
            </a>

            {/* View Mode Switcher */}
            <button
              onClick={() => setViewMode('chunks')}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                viewMode === 'chunks'
                  ? 'bg-emerald-500 text-slate-950 shadow-md shadow-emerald-500/20 font-bold'
                  : 'bg-slate-900 text-slate-400 hover:text-white border border-slate-800'
              }`}
            >
              <Layers className="w-3.5 h-3.5" />
              <span>FAISS Chunks ({effectiveChunks.length})</span>
            </button>

            <button
              onClick={() => setViewMode('text')}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                viewMode === 'text'
                  ? 'bg-emerald-500 text-slate-950 shadow-md shadow-emerald-500/20 font-bold'
                  : 'bg-slate-900 text-slate-400 hover:text-white border border-slate-800'
              }`}
            >
              <Eye className="w-3.5 h-3.5" />
              <span>Raw Text Preview</span>
            </button>
          </div>
        </div>

        {/* Stats Row */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-4">
          {[
            {
              label: 'Total FAISS Chunks',
              value: effectiveChunks.length,
              icon: <Layers className="w-4 h-4 text-emerald-400" />,
              color: 'text-emerald-400',
            },
            {
              label: 'Document Pages',
              value: availablePages.length > 0 ? availablePages.length : '1',
              icon: <BookOpen className="w-4 h-4 text-sky-400" />,
              color: 'text-sky-400',
            },
            {
              label: 'Characters',
              value: totalChars.toLocaleString(),
              icon: <Hash className="w-4 h-4 text-teal-400" />,
              color: 'text-teal-400',
            },
            {
              label: 'Analysis Status',
              value: contractDetail.has_analysis ? 'Indexed & Audited' : 'Indexed',
              icon: <FileCode className="w-4 h-4 text-amber-400" />,
              color: contractDetail.has_analysis ? 'text-emerald-400' : 'text-amber-400',
            },
          ].map((stat, idx) => (
            <div
              key={idx}
              className="p-3 rounded-xl bg-slate-900/50 border border-slate-800/80 flex items-center space-x-3"
            >
              <div className="w-8 h-8 rounded-lg bg-slate-800/80 flex items-center justify-center">
                {stat.icon}
              </div>
              <div>
                <div className={`text-sm font-bold ${stat.color}`}>{stat.value}</div>
                <div className="text-[10px] text-slate-500 uppercase tracking-wider">
                  {stat.label}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Raw Text View */}
      {viewMode === 'text' && (
        <div className="glass-panel rounded-2xl p-6 border border-slate-800 space-y-4">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-semibold text-slate-200 flex items-center space-x-2">
              <Eye className="w-4 h-4 text-emerald-400" />
              <span>Ingested Document Text Stream</span>
            </h4>
            <span className="text-[11px] text-slate-500 font-mono">
              {contractDetail.raw_text_preview?.length || 0} characters
            </span>
          </div>

          <div className="p-4 rounded-xl bg-slate-950 font-mono text-xs text-slate-300 leading-relaxed max-h-[550px] overflow-y-auto whitespace-pre-wrap border border-slate-900 selection:bg-emerald-500/30">
            {contractDetail.raw_text_preview || 'No raw text stream available for this agreement.'}
          </div>
        </div>
      )}

      {/* Chunks Explorer View */}
      {viewMode === 'chunks' && (
        <div className="glass-panel rounded-2xl p-6 border border-slate-800 space-y-4">
          {/* Controls: Search & Page Filter */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center space-x-3">
              <h4 className="text-sm font-semibold text-slate-200 flex items-center space-x-2">
                <Layers className="w-4 h-4 text-emerald-400" />
                <span>FAISS Vector-Indexed Chunks</span>
              </h4>

              {availablePages.length > 1 && (
                <div className="flex items-center space-x-1.5 text-xs">
                  <span className="text-slate-400">Page:</span>
                  <select
                    value={pageFilter}
                    onChange={(e) => setPageFilter(e.target.value)}
                    className="bg-slate-900 border border-slate-800 rounded-lg px-2 py-1 text-xs text-slate-200 outline-none focus:border-emerald-500"
                  >
                    <option value="ALL">All Pages</option>
                    {availablePages.map((p) => (
                      <option key={p} value={p}>
                        Page {p}
                      </option>
                    ))}
                  </select>
                </div>
              )}
            </div>

            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search chunk text, ID, or headings..."
                className="pl-9 pr-4 py-2 bg-slate-950 border border-slate-800 focus:border-emerald-500 rounded-lg text-xs text-slate-200 outline-none transition w-full sm:w-64"
              />
            </div>
          </div>

          {/* Chunk count badge */}
          <div className="flex items-center space-x-2 text-[11px] text-slate-400">
            <Filter className="w-3.5 h-3.5" />
            <span>
              Showing <strong className="text-white">{filteredChunks.length}</strong> of{' '}
              <strong className="text-white">{effectiveChunks.length}</strong> chunks
              {pageFilter !== 'ALL' && (
                <span className="ml-1 text-sky-400">• Filtered to Page {pageFilter}</span>
              )}
              {searchQuery && (
                <span className="ml-1 text-emerald-400">• matching "{searchQuery}"</span>
              )}
            </span>
          </div>

          {/* Chunk Cards */}
          <div className="space-y-3 max-h-[620px] overflow-y-auto pr-1">
            {filteredChunks.map((chunk) => {
              const isTargeted =
                isTargetActive &&
                (activeTargetCitation.chunkId === chunk.chunk_id ||
                  (activeTargetCitation.pageNumber &&
                    activeTargetCitation.pageNumber === chunk.page_number &&
                    !activeTargetCitation.chunkId));

              const isExpanded =
                isTargeted || expandedChunkIdx === chunk.chunk_index;

              return (
                <div
                  key={chunk.chunk_id}
                  ref={isTargeted ? targetedRef : null}
                  className={`rounded-xl transition-all duration-200 overflow-hidden ${
                    isTargeted
                      ? 'border-2 border-emerald-400 bg-emerald-950/20 ring-2 ring-emerald-500/40 shadow-xl shadow-emerald-500/10'
                      : 'bg-slate-900/60 border border-slate-800/80 hover:border-slate-700'
                  }`}
                >
                  {/* Chunk Header */}
                  <div
                    onClick={() =>
                      setExpandedChunkIdx(isExpanded ? null : chunk.chunk_index)
                    }
                    className="p-3.5 cursor-pointer flex items-center justify-between gap-3 select-none"
                  >
                    <div className="flex items-center space-x-3 min-w-0">
                      <div
                        className={`w-8 h-8 rounded-lg flex items-center justify-center font-mono text-xs font-bold flex-shrink-0 ${
                          isTargeted
                            ? 'bg-emerald-500 text-slate-950 ring-2 ring-emerald-400'
                            : 'bg-emerald-500/10 border border-emerald-500/20 text-emerald-400'
                        }`}
                      >
                        {chunk.chunk_index + 1}
                      </div>

                      <div className="min-w-0">
                        <div className="text-xs font-medium text-slate-200 truncate flex items-center space-x-2">
                          <span>{chunk.section_title}</span>
                          {isTargeted && (
                            <span className="px-2 py-0.5 rounded-full bg-emerald-500 text-slate-950 text-[10px] font-extrabold uppercase tracking-wider">
                              Cited Target
                            </span>
                          )}
                        </div>
                        <div className="flex items-center space-x-2 text-[10px] text-slate-500 mt-0.5">
                          {chunk.page_number && (
                            <>
                              <span className="text-slate-400 font-semibold">
                                Page {chunk.page_number}
                              </span>
                              <span>•</span>
                            </>
                          )}
                          <span>{chunk.word_count} words</span>
                          <span>•</span>
                          <span>{chunk.char_count} chars</span>
                          <span>•</span>
                          <span className="font-mono text-slate-400">{chunk.chunk_id}</span>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center space-x-2 flex-shrink-0">
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleCopy(chunk.chunk_id, chunk.text);
                        }}
                        className="p-1.5 rounded-lg text-slate-500 hover:text-emerald-400 hover:bg-slate-800 transition"
                        title="Copy chunk text"
                      >
                        {copiedChunkId === chunk.chunk_id ? (
                          <Check className="w-3.5 h-3.5 text-emerald-400" />
                        ) : (
                          <Copy className="w-3.5 h-3.5" />
                        )}
                      </button>
                      {isExpanded ? (
                        <ChevronUp className="w-4 h-4 text-slate-400" />
                      ) : (
                        <ChevronDown className="w-4 h-4 text-slate-400" />
                      )}
                    </div>
                  </div>

                  {/* Expanded Chunk Content */}
                  {isExpanded && (
                    <div className="px-3.5 pb-3.5 border-t border-slate-800/60">
                      <div className="mt-2 p-3 rounded-lg bg-slate-950 font-mono text-[11px] text-slate-300 leading-relaxed max-h-[320px] overflow-y-auto whitespace-pre-wrap border border-slate-800/80 selection:bg-emerald-500/30">
                        {searchQuery ? (
                          <HighlightedText text={chunk.text} highlight={searchQuery} />
                        ) : (
                          chunk.text
                        )}
                      </div>

                      {/* Metadata tags */}
                      <div className="flex flex-wrap items-center gap-1.5 mt-2.5">
                        <span className="px-2 py-0.5 rounded bg-slate-800 text-[10px] text-slate-400 font-mono">
                          Vector ID: {chunk.chunk_id}
                        </span>
                        {chunk.page_number && (
                          <span className="px-2 py-0.5 rounded bg-sky-500/10 text-[10px] text-sky-400 border border-sky-500/20 font-semibold">
                            Page {chunk.page_number}
                          </span>
                        )}
                        <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-[10px] text-emerald-400 border border-emerald-500/20">
                          FAISS In-Memory Vector
                        </span>
                        <span className="px-2 py-0.5 rounded bg-slate-800 text-[10px] text-slate-400">
                          768-dim Embedding
                        </span>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

function HighlightedText({ text, highlight }) {
  if (!highlight) return text;
  const parts = text.split(new RegExp(`(${highlight.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi'));
  return (
    <>
      {parts.map((part, i) =>
        part.toLowerCase() === highlight.toLowerCase() ? (
          <mark
            key={i}
            className="bg-emerald-500/30 text-emerald-200 rounded px-0.5"
          >
            {part}
          </mark>
        ) : (
          part
        )
      )}
    </>
  );
}
