import { useState, useEffect } from 'react'
import { FileDown, History, ArrowUp, Sparkles } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

export default function FloatingActions({ analysisData, onToggleHistory, onExportPdf }) {
  const [showScroll, setShowScroll] = useState(false)

  useEffect(() => {
    const handleScroll = () => setShowScroll(window.scrollY > 400)
    window.addEventListener('scroll', handleScroll)
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  return (
    <div className="fixed bottom-6 right-6 flex flex-col gap-3 z-30">
      <AnimatePresence>
        {showScroll && (
          <motion.button
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0, opacity: 0 }}
            onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
            className="w-11 h-11 rounded-full glass flex items-center justify-center
                       hover:border-sky-500/30 transition-all shadow-lg shadow-black/20"
          >
            <ArrowUp size={16} className="text-sky-400" />
          </motion.button>
        )}
      </AnimatePresence>

      <motion.button
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        onClick={onToggleHistory}
        className="w-11 h-11 rounded-full glass flex items-center justify-center
                   hover:border-sky-500/30 transition-all shadow-lg shadow-black/20"
        title="Report History"
      >
        <History size={16} className="text-sky-400" />
      </motion.button>

      {analysisData && (
        <motion.button
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={onExportPdf}
          className="w-11 h-11 rounded-full bg-gradient-to-r from-sky-500 to-violet-500
                     flex items-center justify-center shadow-lg shadow-sky-500/30
                     hover:shadow-sky-500/50 transition-shadow"
          title="Export PDF Report"
        >
          <FileDown size={16} className="text-white" />
        </motion.button>
      )}
    </div>
  )
}
