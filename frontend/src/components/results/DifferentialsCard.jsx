import { Brain } from 'lucide-react'

export default function DifferentialsCard({ differentials }) {
  return (
    <div className="glass rounded-2xl p-5">
      <h3 className="text-sm font-semibold text-sky-400 flex items-center gap-2 mb-2">
        <Brain size={16} /> Differential Diagnosis
      </h3>
      <p className="text-[10px] text-slate-600 mb-4">Bayesian-adjusted with clinical context modifiers</p>

      <div className="space-y-2">
        {differentials.map((d, i) => {
          const prob = d.probability ? (d.probability * 100).toFixed(0) : '?'
          const probNum = parseFloat(prob) || 0
          const color = probNum > 60 ? 'text-red-400' : probNum > 30 ? 'text-amber-400' : 'text-sky-400'
          const barColor = probNum > 60 ? 'bg-red-500' : probNum > 30 ? 'bg-amber-500' : 'bg-sky-500'
          const features = d.key_features
            ? (Array.isArray(d.key_features) ? d.key_features.join(', ') : d.key_features)
            : ''

          return (
            <div key={i}>
              <div className="flex items-center gap-3 bg-slate-900/50 rounded-xl px-3 py-2.5 hover:bg-slate-900/70 transition-colors">
                <span className="text-[10px] text-slate-600 w-5 text-center font-bold">#{i + 1}</span>
                <span className="text-xs font-semibold text-slate-200 min-w-[140px]">
                  {d.diagnosis || d.name || 'Unknown'}
                </span>
                <div className="flex-1 h-1.5 bg-slate-800 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${barColor} transition-all duration-500`}
                    style={{ width: `${prob}%` }}
                  />
                </div>
                <span className={`text-xs font-bold tabular-nums min-w-[36px] text-right ${color}`}>
                  {prob}%
                </span>
              </div>
              {features && (
                <p className="text-[10px] text-slate-600 pl-10 mt-0.5 mb-1">{features}</p>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
