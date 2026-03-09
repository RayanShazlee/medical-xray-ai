import { CheckCircle } from 'lucide-react'
import ConfidenceBars from './ConfidenceBars'

export default function DetectionsCard({ detections }) {
  return (
    <div className="glass rounded-2xl p-5 border-l-4 border-emerald-500">
      <h3 className="text-sm font-semibold text-emerald-400 flex items-center gap-2 mb-2">
        <CheckCircle size={16} /> Detection Confidence
      </h3>
      <p className="text-xs text-slate-500 mb-4">
        No significant pathology — Grad-CAM heatmap not generated.
      </p>
      <ConfidenceBars detections={detections} />
      <div className="mt-4 space-y-1 text-[10px] text-slate-600">
        <p>🔬 CheXNet DenseNet-121 (14 pathologies)</p>
        <p>ℹ️ Grad-CAM++ only generated when pathology exceeds confidence threshold.</p>
      </div>
    </div>
  )
}
