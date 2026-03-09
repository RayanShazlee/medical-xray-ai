import { useState, useEffect, useCallback, useRef, Component } from 'react'
import { io } from 'socket.io-client'
import { motion, AnimatePresence } from 'framer-motion'
import Header from './components/Header'
import UploadPanel from './components/UploadPanel'
import ProgressTracker from './components/ProgressTracker'
import ResultsDashboard from './components/ResultsDashboard'
import KnowledgeSearch from './components/KnowledgeSearch'
import MedicalTermLookup from './components/MedicalTermLookup'
import HistorySidebar from './components/HistorySidebar'
import FloatingActions from './components/FloatingActions'
import './App.css'

/* Top-level Error Boundary to prevent blank page */
class AppErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }
  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }
  componentDidCatch(error, info) {
    console.error('[App Error]', error, info)
  }
  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center p-8">
          <div className="glass rounded-2xl p-8 max-w-lg text-center">
            <h2 className="text-xl font-bold text-red-400 mb-2">⚠️ Something went wrong</h2>
            <p className="text-sm text-slate-400 mb-4">{this.state.error?.message}</p>
            <button
              onClick={() => { this.setState({ hasError: false, error: null }); window.location.reload() }}
              className="px-4 py-2 bg-sky-500 text-white rounded-xl text-sm hover:bg-sky-400 transition-colors"
            >
              Reload App
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}

export { AppErrorBoundary }

export default function App() {
  const [analysisData, setAnalysisData] = useState(null)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [progress, setProgress] = useState({ step: '', percent: 0, message: '' })
  const [error, setError] = useState(null)
  const [historyOpen, setHistoryOpen] = useState(false)
  const socketRef = useRef(null)
  const resultsRef = useRef(null)

  useEffect(() => {
    const socket = io({ transports: ['websocket', 'polling'] })
    socket.on('connect', () => console.log('🔌 WebSocket connected'))
    socket.on('analysis_progress', (data) => {
      setProgress({ step: data.step, percent: data.progress, message: data.message })
    })
    socketRef.current = socket
    return () => socket.disconnect()
  }, [])

  const handleUpload = useCallback(async (formData) => {
    setIsAnalyzing(true)
    setError(null)
    setProgress({ step: '', percent: 0, message: '' })
    setAnalysisData(null)
    try {
      const response = await fetch('/upload', { method: 'POST', body: formData })
      const data = await response.json()
      console.log('✅ Upload response status:', response.status)
      console.log('✅ Upload response keys:', Object.keys(data))
      console.log('✅ Has diagnosis:', !!data.diagnosis)
      console.log('✅ Has heatmap:', !!data.heatmap)
      console.log('✅ Has detections:', !!data.detections, 'count:', data.detections?.length)
      if (!response.ok) throw new Error(data.error || 'Analysis failed')
      setAnalysisData(data)
      setProgress({ step: 'complete', percent: 100, message: 'Complete' })
      setTimeout(() => resultsRef.current?.scrollIntoView({ behavior: 'smooth' }), 300)
    } catch (err) {
      console.error('❌ Upload error:', err)
      setError(err.message)
    } finally {
      setIsAnalyzing(false)
    }
  }, [])

  const handleExportPDF = useCallback(async () => {
    if (!analysisData) return
    try {
      const res = await fetch('/export_pdf', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(analysisData),
      })
      if (!res.ok) throw new Error('PDF generation failed')
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `radiology_report_${new Date().toISOString().slice(0, 10)}.pdf`
      a.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      alert(err.message)
    }
  }, [analysisData])

  const handleLoadReport = useCallback(async (reportId) => {
    try {
      const res = await fetch(`/history/${reportId}`)
      const data = await res.json()
      if (data.error) throw new Error(data.error)
      setAnalysisData(data)
      setHistoryOpen(false)
      window.scrollTo({ top: 0, behavior: 'smooth' })
    } catch (err) {
      alert('Failed to load report: ' + err.message)
    }
  }, [])

  return (
    <div className="min-h-screen relative">
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <div className="absolute -top-40 -right-40 w-96 h-96 bg-sky-500/5 rounded-full blur-3xl" />
        <div className="absolute top-1/2 -left-40 w-96 h-96 bg-indigo-500/5 rounded-full blur-3xl" />
        <div className="absolute -bottom-40 right-1/3 w-96 h-96 bg-cyan-500/5 rounded-full blur-3xl" />
      </div>

      <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <Header />
        <div className="mt-8">
          <UploadPanel onUpload={handleUpload} isAnalyzing={isAnalyzing} />
        </div>

        <AnimatePresence>
          {(isAnalyzing || progress.percent > 0) && progress.percent < 100 && (
            <motion.div
              key="progress"
              initial={{ opacity: 0, y: 20, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -20, scale: 0.98 }}
              transition={{ duration: 0.4 }}
              className="mt-6"
            >
              <ProgressTracker progress={progress} />
            </motion.div>
          )}
        </AnimatePresence>

        <AnimatePresence>
          {error && (
            <motion.div
              key="error"
              initial={{ opacity: 0, y: 20, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -20, scale: 0.98 }}
              transition={{ duration: 0.3 }}
              className="mt-6 glass rounded-2xl p-4 border border-red-500/30 bg-red-500/10"
            >
              <p className="text-red-400 flex items-center gap-2">
                <span className="text-xl">⚠️</span> {error}
              </p>
            </motion.div>
          )}
        </AnimatePresence>

        <div ref={resultsRef}>
          <AnimatePresence>
            {analysisData && (
              <motion.div
                key="results"
                initial={{ opacity: 0, y: 40 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, ease: 'easeOut' }}
                className="mt-8"
              >
                <ResultsDashboard data={analysisData} />
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        <div className="mt-8">
          <MedicalTermLookup />
        </div>

        <div className="mt-8">
          <KnowledgeSearch />
        </div>
      </div>

      <HistorySidebar
        isOpen={historyOpen}
        onClose={() => setHistoryOpen(false)}
        onLoadReport={handleLoadReport}
      />
      <FloatingActions
        analysisData={analysisData}
        onExportPdf={handleExportPDF}
        onToggleHistory={() => setHistoryOpen(prev => !prev)}
      />
    </div>
  )
}
