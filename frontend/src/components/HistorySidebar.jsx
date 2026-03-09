import { useState, useEffect } from 'react'
import { X, History, BarChart3 } from 'lucide-react'

export default function HistorySidebar({ isOpen, onClose, onLoadReport }) {
  const [reports, setReports] = useState([])
  const [stats, setStats] = useState(null)

  useEffect(() => {
    if (!isOpen) return
    Promise.all([
      fetch('/history?limit=20').then(r => r.json()),
      fetch('/dashboard').then(r => r.json()),
    ]).then(([historyData, dashData]) => {
      setReports(historyData.reports || [])
      setStats(dashData)
    }).catch(() => {})
  }, [isOpen])

  const getSevColor = (sev) => {
    if (!sev) return 'text-slate-500'
    const s = sev.toLowerCase()
    if (s.includes('severe') || s.includes('critical')) return 'text-red-400'
    if (s.includes('moderate')) return 'text-amber-400'
    return 'text-emerald-400'
  }

  return (
    <>
      {/* Overlay */}
      {isOpen && (
        <div className="fixed inset-0 bg-black/50 z-40 backdrop-blur-sm" onClick={onClose} />
      )}

      {/* Panel */}
      <div className={`fixed top-0 right-0 h-full w-full sm:w-[400px] glass-strong z-50 
                        transform transition-transform duration-300 ease-out overflow-y-auto
                        ${isOpen ? 'translate-x-0' : 'translate-x-full'}`}>
        <div className="p-5">
          <div className="flex items-center justify-between mb-5">
            <h3 className="text-sm font-semibold text-sky-400 flex items-center gap-2">
              <History size={16} /> Report History
            </h3>
            <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-slate-800 transition-colors">
              <X size={16} className="text-slate-500" />
            </button>
          </div>

          {/* Stats */}
          {stats && (
            <div className="grid grid-cols-2 gap-2 mb-5">
              <div className="bg-slate-900/60 rounded-xl p-3 text-center">
                <div className="text-2xl font-black text-sky-400">{stats.total_reports || 0}</div>
                <div className="text-[10px] text-slate-500">Total Reports</div>
              </div>
              <div className="bg-slate-900/60 rounded-xl p-3 text-center">
                <div className="text-2xl font-black text-sky-400">{stats.today_reports || 0}</div>
                <div className="text-[10px] text-slate-500">Today</div>
              </div>
            </div>
          )}

          {stats?.severity_distribution && (
            <div className="mb-5 bg-slate-900/60 rounded-xl p-3">
              <h4 className="text-[10px] text-slate-500 uppercase tracking-wider mb-2 flex items-center gap-1">
                <BarChart3 size={10} /> Severity Distribution
              </h4>
              {Object.entries(stats.severity_distribution).map(([sev, count]) => (
                <div key={sev} className="flex justify-between text-xs py-0.5">
                  <span className="text-slate-400">{sev}</span>
                  <span className="font-bold text-slate-200">{count}</span>
                </div>
              ))}
            </div>
          )}

          {/* Report list */}
          <div className="space-y-2">
            {reports.length > 0 ? reports.map(r => (
              <button
                key={r.report_id}
                onClick={() => onLoadReport(r.report_id)}
                className="w-full text-left bg-slate-900/40 hover:bg-slate-900/70 rounded-xl p-3 
                           border border-transparent hover:border-sky-500/20 transition-all"
              >
                <div className="flex justify-between items-start">
                  <div>
                    <p className="text-xs font-medium text-slate-200">{r.image_filename || 'Unknown'}</p>
                    <p className="text-[10px] text-slate-600 mt-0.5">
                      {r.timestamp ? new Date(r.timestamp).toLocaleString() : '—'}
                    </p>
                  </div>
                  <span className={`text-[10px] font-bold ${getSevColor(r.severity)}`}>
                    {r.severity || 'N/A'}
                  </span>
                </div>
                {r.primary_finding && (
                  <p className="text-[10px] text-sky-400 mt-1 truncate">{r.primary_finding}</p>
                )}
              </button>
            )) : (
              <p className="text-xs text-slate-600 text-center py-6">
                No reports yet. Analyze an X-ray to get started.
              </p>
            )}
          </div>
        </div>
      </div>
    </>
  )
}
