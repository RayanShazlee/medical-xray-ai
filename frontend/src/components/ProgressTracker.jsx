import { Check, Loader2 } from 'lucide-react'

const STEPS = [
  { key: 'enhancement', icon: '🤖', label: 'Enhancement Agent' },
  { key: 'segmentation', icon: '🫁', label: 'Anatomical Segmentation' },
  { key: 'classification', icon: '🔬', label: 'CheXNet Classification' },
  { key: 'uncertainty', icon: '📊', label: 'Uncertainty Quantification' },
  { key: 'gradcam', icon: '🔥', label: 'Grad-CAM++ Heatmap' },
  { key: 'differentials', icon: '🧠', label: 'Differential Diagnosis' },
  { key: 'clinical', icon: '💊', label: 'Clinical Decision Support' },
  { key: 'rag', icon: '📚', label: 'Knowledge Retrieval' },
  { key: 'report', icon: '📋', label: 'Generating Report' },
]

export default function ProgressTracker({ progress }) {
  const currentIdx = STEPS.findIndex(s => s.key === progress.step)

  return (
    <div className="glass rounded-2xl p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-sky-400 flex items-center gap-2">
          <Loader2 size={16} className="animate-spin" />
          Analysis Pipeline
        </h3>
        <span className="text-sky-400 font-bold text-sm tabular-nums animate-pulse">
          {progress.percent}%
        </span>
      </div>

      {/* Progress bar */}
      <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden mb-5">
        <div
          className="h-full rounded-full bg-gradient-to-r from-sky-400 to-indigo-500 transition-all duration-500 ease-out"
          style={{ width: `${progress.percent}%` }}
        />
      </div>

      {/* Steps */}
      <div className="grid grid-cols-3 sm:grid-cols-5 lg:grid-cols-9 gap-3">
        {STEPS.map((step, idx) => {
          const isDone = idx < currentIdx
          const isActive = idx === currentIdx
          return (
            <div
              key={step.key}
              className={`flex flex-col items-center gap-1.5 transition-all duration-300 ${
                isDone ? 'opacity-100' : isActive ? 'opacity-100' : 'opacity-40'
              }`}
            >
              <div
                className={`w-9 h-9 rounded-xl flex items-center justify-center text-sm transition-all duration-300 ${
                  isDone
                    ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                    : isActive
                    ? 'bg-sky-500/20 text-sky-400 border border-sky-500/40 animate-pulse-ring'
                    : 'bg-slate-800 text-slate-600 border border-slate-700'
                }`}
              >
                {isDone ? <Check size={14} /> : step.icon}
              </div>
              <span className={`text-[10px] text-center leading-tight ${
                isActive ? 'text-sky-400 font-medium' : isDone ? 'text-emerald-400' : 'text-slate-600'
              }`}>
                {step.label}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
