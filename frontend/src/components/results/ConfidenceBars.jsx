export default function ConfidenceBars({ detections }) {
  return (
    <div className="space-y-2">
      {detections.map((d, i) => {
        const pct = (d.score * 100).toFixed(1)
        const colorClass =
          d.score > 0.4 ? 'from-red-500 to-orange-500' :
          d.score > 0.2 ? 'from-amber-500 to-yellow-500' :
          'from-sky-500 to-indigo-500'

        return (
          <div key={i} className="bg-slate-900/60 rounded-xl p-2.5">
            <div className="flex justify-between items-center mb-1">
              <span className="text-xs text-slate-300 font-medium">{d.label}</span>
              <span className="text-xs font-bold text-slate-200 tabular-nums">{pct}%</span>
            </div>
            <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full bg-gradient-to-r ${colorClass} transition-all duration-700`}
                style={{ width: `${Math.max(parseFloat(pct), 2)}%` }}
              />
            </div>
          </div>
        )
      })}
    </div>
  )
}
