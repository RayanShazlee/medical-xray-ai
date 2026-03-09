import { Activity, Brain, Scan, Heart, Stethoscope, FileText, Globe, BookOpen } from 'lucide-react'

const features = [
  { icon: Activity, label: 'Enhancement Agent' },
  { icon: Scan, label: '14-Disease Detection' },
  { icon: Brain, label: 'Grad-CAM++' },
  { icon: Heart, label: 'CTR Measurement' },
  { icon: Stethoscope, label: 'Clinical Decision' },
  { icon: FileText, label: 'PDF Reports' },
  { icon: Globe, label: 'Multi-Language' },
  { icon: BookOpen, label: 'Textbook RAG' },
]

export default function Header() {
  return (
    <header className="text-center">
      <div className="flex items-center justify-center gap-3 mb-3">
        <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-sky-400 to-indigo-500 flex items-center justify-center text-2xl shadow-lg shadow-sky-500/20">
          🏥
        </div>
        <h1 className="text-3xl sm:text-4xl font-extrabold gradient-text tracking-tight">
          Medical X-ray AI
        </h1>
      </div>
      <p className="text-slate-400 text-sm mb-4">
        Advanced Clinical Decision Support • CheXNet 14-Pathology • RAG Knowledge Base
      </p>
      <div className="flex flex-wrap justify-center gap-2">
        {features.map(({ icon: Icon, label }) => (
          <span
            key={label}
            className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium
                       bg-sky-400/8 text-sky-300 border border-sky-400/15 hover:border-sky-400/30 transition-colors"
          >
            <Icon size={12} />
            {label}
          </span>
        ))}
      </div>
    </header>
  )
}
