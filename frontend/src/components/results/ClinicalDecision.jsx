import { Stethoscope, Calculator, Pill, TestTube, CalendarCheck, AlertTriangle } from 'lucide-react'

export default function ClinicalDecision({ decision }) {
  const cd = decision

  return (
    <div className="glass rounded-2xl p-5">
      <h3 className="text-sm font-semibold text-sky-400 flex items-center gap-2 mb-4">
        <Stethoscope size={16} /> Clinical Decision Support
      </h3>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* CURB-65 */}
        {cd.curb65 && (
          <div className={`bg-slate-900/50 rounded-2xl p-4 border-l-4 ${
            cd.curb65.score >= 3 ? 'border-red-500' : cd.curb65.score >= 2 ? 'border-amber-500' : 'border-emerald-500'
          }`}>
            <h4 className="text-[10px] text-slate-500 uppercase tracking-wider flex items-center gap-1.5 mb-3">
              <Calculator size={12} /> CURB-65 Severity Score
            </h4>
            <div className="flex items-center gap-4">
              <div className={`text-4xl font-black ${
                cd.curb65.score >= 3 ? 'text-red-400' : cd.curb65.score >= 2 ? 'text-amber-400' : 'text-emerald-400'
              }`}>
                {cd.curb65.score}/5
              </div>
              <div>
                <p className="text-xs font-semibold text-slate-200">{cd.curb65.risk}</p>
                <p className="text-[10px] text-slate-500">Mortality: {cd.curb65.mortality || 'N/A'}</p>
              </div>
            </div>
            {cd.curb65.management && (
              <div className="mt-3 bg-slate-800/50 rounded-lg px-3 py-2 text-xs text-slate-300">
                🏥 {cd.curb65.management}
              </div>
            )}
          </div>
        )}

        {/* Antibiotics */}
        {cd.antibiotics && (
          <div className="bg-slate-900/50 rounded-2xl p-4 border-l-4 border-sky-500">
            <h4 className="text-[10px] text-slate-500 uppercase tracking-wider flex items-center gap-1.5 mb-3">
              <Pill size={12} /> Antibiotic Recommendations
            </h4>
            <div className="space-y-2 text-xs">
              {cd.antibiotics.first_line && (
                <div>
                  <span className="text-emerald-400 font-semibold">1st Line: </span>
                  <span className="text-slate-300">
                    {Array.isArray(cd.antibiotics.first_line) ? cd.antibiotics.first_line.join(', ') : cd.antibiotics.first_line}
                  </span>
                </div>
              )}
              {cd.antibiotics.alternative && (
                <div>
                  <span className="text-amber-400 font-semibold">Alternative: </span>
                  <span className="text-slate-300">
                    {Array.isArray(cd.antibiotics.alternative) ? cd.antibiotics.alternative.join(', ') : cd.antibiotics.alternative}
                  </span>
                </div>
              )}
              {cd.antibiotics.duration && (
                <div className="text-slate-500">Duration: {cd.antibiotics.duration}</div>
              )}
            </div>
            <p className="text-[9px] text-slate-600 mt-2">Based on ATS/IDSA guidelines</p>
          </div>
        )}

        {/* Labs */}
        {cd.labs?.length > 0 && (
          <div className="bg-slate-900/50 rounded-2xl p-4 border-l-4 border-indigo-500">
            <h4 className="text-[10px] text-slate-500 uppercase tracking-wider flex items-center gap-1.5 mb-3">
              <TestTube size={12} /> Recommended Labs
            </h4>
            <div className="divide-y divide-slate-800">
              {cd.labs.map((l, i) => {
                const name = typeof l === 'string' ? l : l.name
                const priority = typeof l === 'object' ? l.priority : null
                const pColor = priority === 'STAT' ? 'text-red-400' : priority === 'Urgent' ? 'text-amber-400' : 'text-emerald-400'
                return (
                  <div key={i} className="flex justify-between py-1.5 text-xs">
                    <span className="text-slate-300">{name}</span>
                    {priority && <span className={`font-bold text-[10px] ${pColor}`}>{priority}</span>}
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {/* Follow-up */}
        {cd.followup && (
          <div className="bg-slate-900/50 rounded-2xl p-4 border-l-4 border-cyan-500">
            <h4 className="text-[10px] text-slate-500 uppercase tracking-wider flex items-center gap-1.5 mb-3">
              <CalendarCheck size={12} /> Imaging Follow-up
            </h4>
            <div className="space-y-1 text-xs text-slate-300">
              {cd.followup.timeline && <p><strong>Timeline:</strong> {cd.followup.timeline}</p>}
              {cd.followup.modality && <p><strong>Modality:</strong> {cd.followup.modality}</p>}
              {cd.followup.reason && <p className="text-slate-500">{cd.followup.reason}</p>}
              {typeof cd.followup === 'string' && <p>{cd.followup}</p>}
            </div>
          </div>
        )}
      </div>

      {/* Disclaimer */}
      <div className="mt-4 bg-amber-500/5 border border-amber-500/15 rounded-xl px-4 py-2.5 flex items-start gap-2">
        <AlertTriangle size={14} className="text-amber-500 mt-0.5 shrink-0" />
        <p className="text-[10px] text-slate-500 leading-relaxed">
          <strong className="text-amber-400">Disclaimer:</strong> Clinical decision support is AI-generated for educational purposes.
          All recommendations must be validated by a licensed healthcare provider.
        </p>
      </div>
    </div>
  )
}
