import React from 'react';
import { AlertTriangle, ShieldAlert, CheckCircle, Flame, BarChart3, Info } from 'lucide-react';

export default function RiskOverview({ analysis }) {
  if (!analysis) return null;

  const score = analysis.overall_risk_score;
  const level = analysis.overall_risk_level;

  const getScoreTheme = (lvl) => {
    switch (lvl) {
      case 'CRITICAL':
        return {
          text: 'text-rose-400',
          bg: 'bg-rose-500/10',
          border: 'border-rose-500/30',
          ring: 'ring-rose-500/40',
          label: 'Critical Exposure',
        };
      case 'HIGH':
        return {
          text: 'text-orange-400',
          bg: 'bg-orange-500/10',
          border: 'border-orange-500/30',
          ring: 'ring-orange-500/40',
          label: 'High Risk Profile',
        };
      case 'MEDIUM':
        return {
          text: 'text-amber-400',
          bg: 'bg-amber-500/10',
          border: 'border-amber-500/30',
          ring: 'ring-amber-500/40',
          label: 'Moderate Risk',
        };
      default:
        return {
          text: 'text-emerald-400',
          bg: 'bg-emerald-500/10',
          border: 'border-emerald-500/30',
          ring: 'ring-emerald-500/40',
          label: 'Low Risk',
        };
    }
  };

  const theme = getScoreTheme(level);

  return (
    <div className="space-y-6">
      {/* Top Banner: Score Gauge + Executive Summary */}
      <div className="glass-panel rounded-2xl p-6 border border-slate-800 grid grid-cols-1 lg:grid-cols-12 gap-6 items-center">
        {/* Left: Risk Score Dial / Gauge */}
        <div className="lg:col-span-4 flex flex-col items-center justify-center p-6 rounded-2xl bg-slate-900/50 border border-slate-800/80 text-center relative overflow-hidden">
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
            Composite Contract Risk Index
          </div>

          <div
            className={`w-32 h-32 rounded-full border-4 flex flex-col items-center justify-center ${theme.border} ${theme.bg} my-2 shadow-xl shadow-black/40`}
          >
            <span className={`text-4xl font-extrabold ${theme.text}`}>{score}</span>
            <span className="text-[10px] text-slate-400 uppercase tracking-widest font-mono">
              / 100
            </span>
          </div>

          <div className={`mt-2 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider border ${theme.border} ${theme.bg} ${theme.text}`}>
            {theme.label} ({level})
          </div>
        </div>

        {/* Right: Executive Summary & Key Vulnerabilities */}
        <div className="lg:col-span-8 space-y-4">
          <div>
            <div className="flex items-center space-x-2 text-xs font-semibold text-emerald-400 uppercase tracking-wider mb-1">
              <Info className="w-4 h-4" />
              <span>Executive Risk Summary</span>
            </div>
            <p className="text-sm text-slate-300 leading-relaxed bg-slate-900/40 p-4 rounded-xl border border-slate-800/80">
              {analysis.executive_summary}
            </p>
          </div>

          {/* Key Vulnerabilities */}
          <div>
            <div className="text-xs font-semibold text-rose-400 uppercase tracking-wider flex items-center space-x-1.5 mb-2">
              <Flame className="w-4 h-4" />
              <span>Priority Red Flags</span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
              {analysis.key_vulnerabilities?.map((vuln, idx) => (
                <div
                  key={idx}
                  className="flex items-start space-x-2 p-2.5 rounded-lg bg-rose-500/5 border border-rose-500/20 text-xs text-rose-300"
                >
                  <AlertTriangle className="w-4 h-4 text-rose-400 flex-shrink-0 mt-0.5" />
                  <span>{vuln}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Category Risk Breakdown */}
      {analysis.category_breakdowns && analysis.category_breakdowns.length > 0 && (
        <div className="glass-panel rounded-2xl p-6 border border-slate-800">
          <div className="flex items-center space-x-2 text-sm font-semibold text-white mb-4">
            <BarChart3 className="w-4 h-4 text-emerald-400" />
            <span>Category Exposure Metrics</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {analysis.category_breakdowns.map((cat, idx) => {
              const catTheme = getScoreTheme(cat.level);
              return (
                <div
                  key={idx}
                  className="p-4 rounded-xl bg-slate-900/50 border border-slate-800 space-y-3"
                >
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold text-slate-200">{cat.category}</span>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${catTheme.bg} ${catTheme.text} border ${catTheme.border}`}>
                      {cat.level}
                    </span>
                  </div>

                  {/* Progress bar */}
                  <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                    <div
                      className={`h-full transition-all duration-500 ${
                        cat.level === 'CRITICAL'
                          ? 'bg-rose-500'
                          : cat.level === 'HIGH'
                          ? 'bg-orange-500'
                          : cat.level === 'MEDIUM'
                          ? 'bg-amber-500'
                          : 'bg-emerald-500'
                      }`}
                      style={{ width: `${Math.min(cat.score, 100)}%` }}
                    />
                  </div>

                  <div className="flex justify-between text-[11px] text-slate-400">
                    <span>Risk Score: {cat.score}/100</span>
                    <span>{cat.clauses_flagged} flagged clauses</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
