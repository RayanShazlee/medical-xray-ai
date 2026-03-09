import { BarChart3 } from 'lucide-react'

const RELIABILITY_STYLES = {
  HIGH: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
  MODERATE: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
  LOW: 'bg-red-500/15 text-red-400 border-red-500/30',
  VERY_LOW: 'bg-red-500/25 text-red-300 border-red-500/40',
}

export default function UncertaintyCard({ uncertainty }) {
  // Backend sends reliability as "HIGH — Consistent predictions across samples"
  // Extract just the first word (HIGH, MODERATE, LOW, VERY) for style lookup
  const rawReliability = uncertainty.reliability || uncertainty.confidence_level || 'MODERATE'
  const reliabilityKey = rawReliability.split('—')[0].trim().replace(/\s+/g, '_')
  const reliability = RELIABILITY_STYLES[reliabilityKey] ? reliabilityKey : 
    rawReliability.startsWith('HIGH') ? 'HIGH' :
    rawReliability.startsWith('LOW') ? 'LOW' :
    rawReliability.startsWith('VERY') ? 'VERY_LOW' : 'MODERATE'
  const reliabilityLabel = rawReliability.includes('—') ? rawReliability.split('—')[0].trim() : rawReliability
  
  const meanConf = uncertainty.mean_confidence ? (uncertainty.mean_confidence * 100).toFixed(1) : '—'
  
  // Get the raw std value — backend sends std_confidence as a small float (e.g. 0.02)
  const rawStd = uncertainty.std_confidence ?? uncertainty.mean_std ?? null
  const stdConf = rawStd != null ? (rawStd * 100).toFixed(2) : '—'
  const nPasses = uncertainty.n_forward || uncertainty.n_forward_passes || uncertainty.mc_dropout_runs || 15
  const stdNum = parseFloat(stdConf) || 0

  const varianceColor = stdNum < 5 ? 'bg-emerald-500' : stdNum < 10 ? 'bg-amber-500' : 'bg-red-500'

  return (
    <div className="glass rounded-2xl p-5">
      <h3 className="text-sm font-semibold text-sky-400 flex items-center gap-2 mb-4">
        <BarChart3 size={16} /> Uncertainty Quantification
      </h3>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {/* Mean confidence */}
        <div className="flex flex-col items-center justify-center bg-slate-900/40 rounded-2xl p-5">
          <div className="text-4xl font-black text-sky-400 mb-1">{meanConf}%</div>
          <div className="text-xs text-slate-500">Mean Confidence</div>
          <span className={`mt-2 px-3 py-1 rounded-full text-[10px] font-bold border ${RELIABILITY_STYLES[reliability]}`}>
            {reliabilityLabel} Reliability
          </span>
        </div>

        {/* Variance */}
        <div className="md:col-span-2 bg-slate-900/40 rounded-2xl p-5">
          <div className="flex justify-between items-center mb-3">
            <span className="text-xs text-slate-400">Prediction Variance (σ)</span>
            <span className="text-sm font-bold text-slate-200">±{stdConf}%</span>
          </div>
          <div className="h-2 bg-slate-800 rounded-full overflow-hidden mb-3">
            <div
              className={`h-full rounded-full ${varianceColor} transition-all duration-700`}
              style={{ width: `${Math.min(100, stdNum * 10)}%` }}
            />
          </div>
          <p className="text-[10px] text-slate-600 leading-relaxed">
            ℹ️ Based on {nPasses} stochastic forward passes with dropout enabled.
            Lower variance = more consistent predictions.
          </p>
        </div>
      </div>
    </div>
  )
}
