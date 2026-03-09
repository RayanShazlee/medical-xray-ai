import { Bot, CheckCircle, AlertTriangle } from 'lucide-react'

const ISSUE_ICONS = {
  underexposed: '🌑', overexposed: '☀️', low_contrast: '🔲',
  noisy: '📡', blurry: '🔍', compressed_range: '📊',
}

export default function QualityReport({ report }) {
  const isGood = report.quality === 'good'

  return (
    <div className={`glass rounded-2xl p-5 border-l-4 ${isGood ? 'border-emerald-500' : 'border-amber-500'}`}>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-sky-400 flex items-center gap-2">
          <Bot size={16} /> Enhancement Agent
        </h3>
        <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold ${
          isGood
            ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
            : 'bg-amber-500/15 text-amber-400 border border-amber-500/30'
        }`}>
          {isGood ? <CheckCircle size={12} /> : <AlertTriangle size={12} />}
          {isGood ? 'GOOD' : 'ENHANCED'}
        </span>
      </div>

      {/* Issues */}
      <div className="mb-3">
        <p className="text-[11px] text-slate-500 uppercase tracking-wider mb-1.5">Issues</p>
        <div className="flex flex-wrap gap-1.5">
          {report.issues?.length > 0 ? report.issues.map(issue => (
            <span key={issue} className="px-2 py-0.5 rounded-lg bg-amber-500/10 text-amber-400 text-xs border border-amber-500/20">
              {ISSUE_ICONS[issue] || '⚠️'} {issue.replace(/_/g, ' ')}
            </span>
          )) : (
            <span className="px-2 py-0.5 rounded-lg bg-emerald-500/10 text-emerald-400 text-xs">✅ No issues</span>
          )}
        </div>
      </div>

      {/* Corrections */}
      {report.actions_applied?.length > 0 && (
        <div className="mb-3">
          <p className="text-[11px] text-slate-500 uppercase tracking-wider mb-1.5">Corrections Applied</p>
          <div className="flex flex-wrap gap-1.5">
            {report.actions_applied.map(action => (
              <span key={action} className="px-2 py-0.5 rounded-lg bg-sky-400/10 text-sky-300 text-xs border border-sky-400/20">
                🔧 {action}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Metrics */}
      {report.metrics && (
        <div className="grid grid-cols-3 gap-2 mt-3">
          {[
            { label: 'Brightness', val: report.metrics.brightness, bad: v => v < 60 || v > 190 },
            { label: 'Contrast', val: report.metrics.contrast, bad: v => v < 35 },
            { label: 'Sharpness', val: report.metrics.sharpness, bad: v => v < 15 },
          ].map(m => (
            <div key={m.label} className="bg-slate-900/60 rounded-xl p-2.5 text-center">
              <p className="text-[10px] text-slate-500">{m.label}</p>
              <p className={`text-lg font-bold ${m.bad(m.val) ? 'text-amber-400' : 'text-emerald-400'}`}>
                {typeof m.val === 'number' ? m.val.toFixed(0) : m.val}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
