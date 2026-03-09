import { Flame } from 'lucide-react'
import ConfidenceBars from './ConfidenceBars'

export default function GradCAMCard({ heatmap, detections }) {
  const primary = detections?.[0]
  const primaryScore = primary ? (primary.score * 100).toFixed(1) : '—'
  const primaryColor = primary?.score > 0.4 ? 'text-red-400' : primary?.score > 0.2 ? 'text-amber-400' : 'text-sky-400'

  return (
    <div className="glass rounded-2xl p-5">
      <h3 className="text-sm font-semibold text-sky-400 flex items-center gap-2 mb-4">
        <Flame size={16} /> Grad-CAM++ Disease Localization
      </h3>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* Heatmap */}
        <div className="lg:col-span-3 flex justify-center relative">
          <div className="relative inline-block">
            <img
              src={`data:image/png;base64,${heatmap}`}
              alt="Grad-CAM heatmap"
              className="max-h-[500px] rounded-xl border-2 border-sky-500/30"
            />
            {/* Floating certainty badge */}
            <div className="absolute top-3 right-3 glass-strong rounded-xl px-3 py-2 text-center border border-sky-500/30">
              <div className={`text-2xl font-black ${primaryColor}`}>{primaryScore}%</div>
              <div className="text-[10px] text-slate-500">{primary?.label || 'Analysis'}</div>
            </div>
          </div>
          <div className="absolute bottom-3 left-1/2 -translate-x-1/2 glass-strong rounded-lg px-3 py-1.5">
            <p className="text-[10px] text-slate-500 whitespace-nowrap">
              🔴 High certainty &nbsp; 🔵 Low &nbsp; 🟢 Lung boundary
            </p>
          </div>
        </div>

        {/* Detections sidebar */}
        <div className="lg:col-span-2">
          <h4 className="text-xs text-slate-500 uppercase tracking-wider mb-3">Detection Confidence</h4>
          {detections?.length > 0 ? (
            <ConfidenceBars detections={detections} />
          ) : (
            <p className="text-xs text-slate-600">No significant pathology detected.</p>
          )}
          <div className="mt-5 space-y-1 text-[10px] text-slate-600">
            <p>🔬 CheXNet DenseNet-121</p>
            <p>📐 Grad-CAM++ (pixel-wise weighting)</p>
            <p>🎯 Highest certainty pathology focus</p>
          </div>
        </div>
      </div>
    </div>
  )
}
