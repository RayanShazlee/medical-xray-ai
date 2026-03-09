import { Sparkles } from 'lucide-react'

export default function EnhancedComparison({ imageB64 }) {
  return (
    <div className="glass rounded-2xl p-5">
      <h3 className="text-sm font-semibold text-sky-400 flex items-center gap-2 mb-3">
        <Sparkles size={16} /> Image Enhancement
      </h3>
      <p className="text-xs text-slate-500 mb-3">Left: Original &nbsp;|&nbsp; Right: CLAHE + Denoising + Sharpening</p>
      <div className="flex justify-center">
        <img
          src={`data:image/png;base64,${imageB64}`}
          alt="Enhancement comparison"
          className="max-h-96 rounded-xl border border-slate-700"
        />
      </div>
    </div>
  )
}
