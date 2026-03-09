import { FileText, Globe } from 'lucide-react'

const LANG_NAMES = {
  en: 'English', ar: 'Arabic', ur: 'Urdu', hi: 'Hindi', es: 'Spanish',
  fr: 'French', de: 'German', zh: 'Chinese', pt: 'Portuguese', tr: 'Turkish', ru: 'Russian',
}

const SEVERITY_STYLES = {
  normal: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
  mild: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
  moderate: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
  severe: 'bg-red-500/15 text-red-400 border-red-500/30',
  critical: 'bg-red-500/25 text-red-300 border-red-500/40',
}

function getSeverityStyle(severity) {
  if (!severity) return ''
  const lower = severity.toLowerCase()
  if (lower.includes('critical')) return SEVERITY_STYLES.critical
  if (lower.includes('severe')) return SEVERITY_STYLES.severe
  if (lower.includes('moderate')) return SEVERITY_STYLES.moderate
  if (lower.includes('mild')) return SEVERITY_STYLES.mild
  return SEVERITY_STYLES.normal
}

function formatDiagnosis(text) {
  return text
    .replace(/\*\*(.*?)\*\*/g, '<strong class="text-sky-300">$1</strong>')
    .replace(/#{1,3}\s*(.*?)(?:\n|$)/g, '<h6 class="text-sky-400 font-semibold mt-4 mb-1 text-sm">$1</h6>')
    .replace(
      /- \*\*(Opacity Pattern|Distribution|Laterality|Severity Grade|Associated Findings|Suspected Etiology|Silhouette Sign)\*\*:\s*(.*?)(?=<br>|$)/g,
      '<div class="flex gap-2 my-1 px-3 py-1.5 bg-slate-900/50 rounded-lg border-l-2 border-sky-500/40 text-xs"><span class="text-slate-500 shrink-0 min-w-[130px]">$1</span><span class="text-slate-200 font-medium">$2</span></div>'
    )
    .replace(/\n/g, '<br>')
}

export default function DiagnosisReport({ diagnosis, severity, language }) {
  return (
    <div className="glass rounded-2xl p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-sky-400 flex items-center gap-2">
          <FileText size={16} /> AI Radiological Report
        </h3>
        <div className="flex items-center gap-2">
          {language && language !== 'en' && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-indigo-500/15 text-indigo-400 text-[10px] border border-indigo-500/20">
              <Globe size={10} /> {LANG_NAMES[language] || language}
            </span>
          )}
          {severity && (
            <span className={`px-3 py-1 rounded-full text-xs font-bold uppercase border ${getSeverityStyle(severity)}`}>
              {severity}
            </span>
          )}
        </div>
      </div>

      <div
        className="text-sm text-slate-300 leading-relaxed prose-invert max-w-none"
        dangerouslySetInnerHTML={{ __html: formatDiagnosis(diagnosis) }}
      />
    </div>
  )
}
