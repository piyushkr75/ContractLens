import React, { useState, useRef } from 'react';
import {
  Download,
  FileBarChart2,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
  ShieldCheck,
  TrendingUp,
  Clock,
  Scale,
  Target,
  Sparkles,
  Loader2,
  Sliders,
  HelpCircle,
  FileQuestion,
} from 'lucide-react';

const PRESET_POLICIES = [
  {
    id: 'default',
    label: 'Standard Commercial Baseline (Default)',
    text: '',
  },
  {
    id: 'strict_buyer',
    label: 'Strict Enterprise Buyer Policy',
    text: 'Policy Requirements: 1) Vendor indemnification must be uncapped for IP infringement, confidentiality, and data breaches. 2) Customer liability must not exceed 1x fees paid in previous 12 months. 3) Payment terms must be Net 45 days. 4) Customer may terminate for convenience with 30 days notice without early termination penalties. 5) Automatic renewal must require 60-day advance written notice.',
  },
  {
    id: 'saas_vendor',
    label: 'Balanced SaaS Vendor Checklist',
    text: 'Policy Requirements: 1) Aggregate liability capped strictly to total fees paid in the trailing 12 months. 2) Mutual exclusion of consequential, punitive, and indirect damages. 3) Standard confidentiality with 3-year survival. 4) Payment due within 30 days; late interest allowed at 1.5% per month. 5) No post-termination non-compete on personnel.',
  },
  {
    id: 'custom',
    label: 'Custom Policy Checklist...',
    text: '',
  },
];

export default function RiskReport({
  analysis,
  filename,
  contractId,
  onSelectCitation,
  onReAnalyze,
  loadingAnalysis = false,
}) {
  const [expandedSections, setExpandedSections] = useState({
    executive: true,
    vulnerabilities: true,
    categories: true,
    clauses: true,
  });
  const [selectedPolicyPreset, setSelectedPolicyPreset] = useState('default');
  const [customPolicyText, setCustomPolicyText] = useState('');
  const [policyExpanded, setPolicyExpanded] = useState(false);
  const reportRef = useRef(null);

  if (!analysis) return null;

  const toggleSection = (key) => {
    setExpandedSections((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const getLevelColor = (level) => {
    switch (level) {
      case 'CRITICAL':
        return 'text-rose-400';
      case 'HIGH':
        return 'text-orange-400';
      case 'MEDIUM':
        return 'text-amber-400';
      default:
        return 'text-emerald-400';
    }
  };

  const getLevelBg = (level) => {
    switch (level) {
      case 'CRITICAL':
        return 'bg-rose-500/10 border-rose-500/30';
      case 'HIGH':
        return 'bg-orange-500/10 border-orange-500/30';
      case 'MEDIUM':
        return 'bg-amber-500/10 border-amber-500/30';
      default:
        return 'bg-emerald-500/10 border-emerald-500/30';
    }
  };

  const handleRunPolicyAnalysis = () => {
    if (!onReAnalyze) return;
    let policyText = '';
    if (selectedPolicyPreset === 'custom') {
      policyText = customPolicyText.trim();
    } else {
      const found = PRESET_POLICIES.find((p) => p.id === selectedPolicyPreset);
      policyText = found ? found.text : '';
    }
    onReAnalyze(policyText || null);
  };

  const handleExportText = () => {
    const lines = [
      '═══════════════════════════════════════════════════════════',
      '  CONTRACTLENS™ — AI CONTRACT RISK INTELLIGENCE REPORT',
      '═══════════════════════════════════════════════════════════',
      '',
      `Document:         ${filename}`,
      `Report Generated: ${new Date().toLocaleString()}`,
      `Risk Score:       ${analysis.overall_risk_score}/100 (${analysis.overall_risk_level})`,
      '',
      '───────────────────────────────────────────────────────────',
      '  EXECUTIVE RISK SUMMARY',
      '───────────────────────────────────────────────────────────',
      '',
      analysis.executive_summary,
      '',
      '───────────────────────────────────────────────────────────',
      '  PRIORITY RED FLAGS',
      '───────────────────────────────────────────────────────────',
      '',
      ...(analysis.key_vulnerabilities || []).map((v, i) => `  ${i + 1}. ${v}`),
      '',
      '───────────────────────────────────────────────────────────',
      '  CATEGORY RISK BREAKDOWN',
      '───────────────────────────────────────────────────────────',
      '',
      ...(analysis.category_breakdowns || []).map(
        (cat) =>
          `  ${cat.category.padEnd(32)} Score: ${String(cat.score).padEnd(3)}/100  Level: ${cat.level.padEnd(8)}  Flagged: ${cat.clauses_flagged}`
      ),
      '',
      '───────────────────────────────────────────────────────────',
      '  CLAUSE-LEVEL RISK ANALYSIS & EVIDENCE',
      '───────────────────────────────────────────────────────────',
      '',
      ...(analysis.clauses || []).flatMap((clause, i) => [
        `  Clause ${i + 1}: ${clause.clause_title}`,
        `  Category: ${clause.category}`,
        `  Presence Status: ${clause.presence_status || 'PRESENT'}`,
        `  Review Priority: ${clause.review_priority || clause.risk_level}`,
        `  Cited Chunk ID: ${clause.cited_chunk_id || 'N/A'}`,
        `  Original Text: "${clause.cited_evidence || clause.original_text}"`,
        `  Explanation: ${clause.explanation || clause.risk_reasoning}`,
        clause.policy_mismatch ? `  Policy Mismatch: ${clause.policy_mismatch}` : '',
        clause.missing_information ? `  Missing Info: ${clause.missing_information}` : '',
        clause.suggested_questions && clause.suggested_questions.length > 0
          ? `  Counsel Questions: ${clause.suggested_questions.join('; ')}`
          : '',
        clause.suggested_revision ? `  Suggested Revision: ${clause.suggested_revision}` : '',
        '',
      ]),
      '',
      '═══════════════════════════════════════════════════════════',
      '  END OF REPORT — ContractLens AI Risk Intelligence',
      '═══════════════════════════════════════════════════════════',
    ];

    const blob = new Blob([lines.filter(Boolean).join('\n')], {
      type: 'text/plain;charset=utf-8',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `ContractLens_Risk_Report_${filename.replace(/\.[^.]+$/, '')}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleExportJSON = () => {
    const blob = new Blob([JSON.stringify(analysis, null, 2)], {
      type: 'application/json;charset=utf-8',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `ContractLens_Risk_Report_${filename.replace(/\.[^.]+$/, '')}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const criticalCount = (analysis.clauses || []).filter(
    (c) => (c.review_priority || c.risk_level) === 'CRITICAL'
  ).length;
  const highCount = (analysis.clauses || []).filter(
    (c) => (c.review_priority || c.risk_level) === 'HIGH'
  ).length;
  const mediumCount = (analysis.clauses || []).filter(
    (c) => (c.review_priority || c.risk_level) === 'MEDIUM'
  ).length;
  const lowCount = (analysis.clauses || []).filter(
    (c) => (c.review_priority || c.risk_level) === 'LOW'
  ).length;

  return (
    <div className="glass-panel rounded-2xl p-6 border border-slate-800 space-y-6">
      {/* Report Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h3 className="text-base font-semibold text-white flex items-center space-x-2">
            <FileBarChart2 className="w-5 h-5 text-emerald-400" />
            <span>Risk Intelligence Report & Policy Audit</span>
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">
            Comprehensive audit for "{filename}" • Verified FAISS chunk citations
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={handleExportText}
            className="flex items-center space-x-1.5 px-3 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-xs font-medium text-slate-300 border border-slate-800 transition"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Export TXT</span>
          </button>
          <button
            onClick={handleExportJSON}
            className="flex items-center space-x-1.5 px-3 py-2 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-xs font-semibold text-white shadow-md shadow-emerald-600/20 transition"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Export JSON</span>
          </button>
        </div>
      </div>

      {/* Review Policy / Illustrative Checklist Selector Card */}
      <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800/80 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2 text-xs font-semibold text-slate-200">
            <Sliders className="w-4 h-4 text-emerald-400" />
            <span>Audit Against Review Policy / Illustrative Checklist</span>
          </div>
          <button
            type="button"
            onClick={() => setPolicyExpanded(!policyExpanded)}
            className="text-[11px] text-emerald-400 hover:text-emerald-300 transition"
          >
            {policyExpanded ? 'Collapse Policy Options' : 'Configure Policy'}
          </button>
        </div>

        {policyExpanded && (
          <div className="space-y-3 pt-2 text-xs">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {PRESET_POLICIES.map((preset) => (
                <button
                  key={preset.id}
                  type="button"
                  onClick={() => setSelectedPolicyPreset(preset.id)}
                  className={`p-2.5 rounded-lg text-left transition border ${
                    selectedPolicyPreset === preset.id
                      ? 'bg-emerald-500/10 border-emerald-500/40 text-emerald-300 font-semibold shadow-sm'
                      : 'bg-slate-950/80 border-slate-800 text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <div className="text-xs">{preset.label}</div>
                </button>
              ))}
            </div>

            {selectedPolicyPreset === 'custom' && (
              <textarea
                value={customPolicyText}
                onChange={(e) => setCustomPolicyText(e.target.value)}
                placeholder="Enter specific policy requirements to evaluate clauses against (e.g. Indemnity must be mutual; liability cap cannot exceed $1M; payment Net 30)..."
                rows={3}
                className="w-full bg-slate-950 border border-slate-800 focus:border-emerald-500 rounded-lg p-2.5 text-xs text-slate-200 outline-none transition"
              />
            )}

            <div className="flex justify-end pt-1">
              <button
                type="button"
                disabled={loadingAnalysis}
                onClick={handleRunPolicyAnalysis}
                className="inline-flex items-center space-x-1.5 px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold shadow-md shadow-emerald-600/20 transition disabled:opacity-50"
              >
                {loadingAnalysis ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    <span>Evaluating Against Policy...</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="w-3.5 h-3.5" />
                    <span>Run Policy Audit</span>
                  </>
                )}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Risk Distribution Summary */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          {
            label: 'Critical Priority',
            count: criticalCount,
            color: 'text-rose-400',
            bg: 'bg-rose-500/10 border-rose-500/20',
          },
          {
            label: 'High Priority',
            count: highCount,
            color: 'text-orange-400',
            bg: 'bg-orange-500/10 border-orange-500/20',
          },
          {
            label: 'Medium Priority',
            count: mediumCount,
            color: 'text-amber-400',
            bg: 'bg-amber-500/10 border-amber-500/20',
          },
          {
            label: 'Low Priority',
            count: lowCount,
            color: 'text-emerald-400',
            bg: 'bg-emerald-500/10 border-emerald-500/20',
          },
        ].map((item, idx) => (
          <div
            key={idx}
            className={`p-3 rounded-xl border flex items-center space-x-3 ${item.bg}`}
          >
            <div className={`text-2xl font-extrabold ${item.color}`}>{item.count}</div>
            <div>
              <div className={`text-xs font-semibold ${item.color}`}>{item.label}</div>
              <div className="text-[10px] text-slate-500">Clauses Flagged</div>
            </div>
          </div>
        ))}
      </div>

      {/* Expandable Sections */}
      <div ref={reportRef} className="space-y-4">
        {/* Executive Summary */}
        <CollapsibleSection
          title="Executive Risk Summary"
          icon={<TrendingUp className="w-4 h-4 text-emerald-400" />}
          expanded={expandedSections.executive}
          onToggle={() => toggleSection('executive')}
        >
          <p className="text-xs text-slate-300 leading-relaxed p-4 rounded-xl bg-slate-950/60 border border-slate-800/60">
            {analysis.executive_summary}
          </p>
        </CollapsibleSection>

        {/* Key Vulnerabilities */}
        <CollapsibleSection
          title="Priority Red Flags"
          icon={<AlertTriangle className="w-4 h-4 text-rose-400" />}
          expanded={expandedSections.vulnerabilities}
          onToggle={() => toggleSection('vulnerabilities')}
        >
          <div className="space-y-2">
            {(analysis.key_vulnerabilities || []).map((vuln, idx) => (
              <div
                key={idx}
                className="flex items-start space-x-2 p-3 rounded-lg bg-rose-500/5 border border-rose-500/15 text-xs text-rose-300"
              >
                <AlertTriangle className="w-4 h-4 text-rose-400 flex-shrink-0 mt-0.5" />
                <span>{vuln}</span>
              </div>
            ))}
          </div>
        </CollapsibleSection>

        {/* Category Breakdown */}
        <CollapsibleSection
          title="Category Exposure Breakdown"
          icon={<Scale className="w-4 h-4 text-teal-400" />}
          expanded={expandedSections.categories}
          onToggle={() => toggleSection('categories')}
        >
          <div className="space-y-2">
            {(analysis.category_breakdowns || []).map((cat, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between p-3 rounded-lg bg-slate-900/50 border border-slate-800/80"
              >
                <div className="flex items-center space-x-3">
                  <span className="text-xs font-medium text-slate-200">{cat.category}</span>
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-bold border ${getLevelBg(
                      cat.level
                    )} ${getLevelColor(cat.level)}`}
                  >
                    {cat.level}
                  </span>
                </div>
                <div className="flex items-center space-x-4 text-[11px] text-slate-400">
                  <span>
                    Score: <strong className="text-white">{cat.score}</strong>/100
                  </span>
                  <span>{cat.clauses_flagged} flagged</span>
                </div>
              </div>
            ))}
          </div>
        </CollapsibleSection>

        {/* All Clauses Detailed with Grounded Citations */}
        <CollapsibleSection
          title={`All Audited Clauses (${(analysis.clauses || []).length})`}
          icon={<ShieldCheck className="w-4 h-4 text-sky-400" />}
          expanded={expandedSections.clauses}
          onToggle={() => toggleSection('clauses')}
        >
          <div className="space-y-3">
            {(analysis.clauses || []).map((clause) => {
              const priority = clause.review_priority || clause.risk_level || 'MEDIUM';
              return (
                <div
                  key={clause.id}
                  className="p-4 rounded-xl bg-slate-900/40 border border-slate-800/80 space-y-3"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="space-y-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span
                          className={`px-2 py-0.5 rounded-full text-[10px] font-bold border uppercase ${getLevelBg(
                            priority
                          )} ${getLevelColor(priority)}`}
                        >
                          {priority} Priority
                        </span>
                        {clause.presence_status && (
                          <span className="text-[10px] text-slate-400 px-2 py-0.5 rounded bg-slate-800 border border-slate-700">
                            {clause.presence_status}
                          </span>
                        )}
                        <span className="text-[10px] text-slate-400 px-2 py-0.5 rounded bg-slate-800">
                          {clause.category}
                        </span>
                      </div>
                      <h5 className="text-xs font-semibold text-slate-200 pt-0.5">
                        {clause.clause_title}
                      </h5>
                    </div>

                    {/* Jump to Document Viewer Citation */}
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
                        className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-lg bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 text-[10px] font-semibold transition"
                      >
                        <Target className="w-3 h-3" />
                        <span>Focus Citation</span>
                      </button>
                    )}
                  </div>

                  <blockquote className="p-2.5 rounded-lg bg-slate-950 font-mono text-[11px] text-slate-300 leading-relaxed border-l-2 border-slate-700">
                    "{clause.cited_evidence || clause.original_text || 'No text excerpt.'}"
                  </blockquote>

                  {/* Explanation */}
                  <div className="p-2.5 rounded-lg bg-slate-950/60 border border-slate-800 text-[11px] text-slate-300">
                    <span className="font-semibold block mb-0.5 text-slate-200">
                      Risk Explanation
                    </span>
                    {clause.explanation || clause.risk_reasoning}
                  </div>

                  {/* Policy mismatch */}
                  {clause.policy_mismatch && (
                    <div className="p-2.5 rounded-lg bg-amber-500/10 border border-amber-500/20 text-[11px] text-amber-300">
                      <span className="font-semibold block mb-0.5 text-amber-400">
                        Review Policy Mismatch
                      </span>
                      {clause.policy_mismatch}
                    </div>
                  )}

                  {/* Suggested questions for counsel */}
                  {clause.suggested_questions && clause.suggested_questions.length > 0 && (
                    <div className="p-2.5 rounded-lg bg-slate-950/80 border border-slate-800 text-[11px] space-y-1">
                      <span className="font-semibold text-indigo-400 flex items-center space-x-1">
                        <HelpCircle className="w-3.5 h-3.5" />
                        <span>Questions for Human Review</span>
                      </span>
                      <ul className="list-disc pl-4 text-slate-400 space-y-0.5">
                        {clause.suggested_questions.map((q, qIdx) => (
                          <li key={qIdx}>{q}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Suggested Redline */}
                  {clause.suggested_revision && (
                    <div className="p-2.5 rounded-lg bg-slate-950/80 border border-teal-500/20">
                      <span className="font-semibold text-teal-400 text-[10px] uppercase tracking-wider block mb-1">
                        Suggested Redline
                      </span>
                      <p className="text-[11px] text-slate-300 font-mono leading-relaxed">
                        {clause.suggested_revision}
                      </p>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </CollapsibleSection>
      </div>

      {/* Report Timestamp */}
      <div className="pt-3 border-t border-slate-800 flex items-center justify-between text-[10px] text-slate-500">
        <span className="flex items-center space-x-1">
          <Clock className="w-3 h-3" />
          <span>
            Report Analyzed:{' '}
            {analysis.analyzed_at ? new Date(analysis.analyzed_at).toLocaleString() : 'N/A'}
          </span>
        </span>
        <span>ContractLens™ AI Risk Intelligence & In-Memory FAISS Engine</span>
      </div>
    </div>
  );
}

function CollapsibleSection({ title, icon, expanded, onToggle, children }) {
  return (
    <div className="rounded-xl bg-slate-900/30 border border-slate-800/60 overflow-hidden">
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between p-3 text-left hover:bg-slate-800/30 transition"
      >
        <div className="flex items-center space-x-2">
          {icon}
          <span className="text-xs font-semibold text-slate-200">{title}</span>
        </div>
        {expanded ? (
          <ChevronUp className="w-4 h-4 text-slate-400" />
        ) : (
          <ChevronDown className="w-4 h-4 text-slate-400" />
        )}
      </button>

      {expanded && <div className="px-3 pb-3">{children}</div>}
    </div>
  );
}
