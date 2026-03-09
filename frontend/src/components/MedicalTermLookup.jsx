import { useState, useRef, useEffect } from 'react'
import { Search, Loader2, BookHeart, Volume2, Lightbulb, Link2, HeartPulse, Sparkles, X, ArrowRight, HelpCircle } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

const COMMON_TERMS = [
  'Cardiomegaly',
  'Pneumothorax',
  'Pleural Effusion',
  'Atelectasis',
  'Consolidation',
  'Infiltrate',
  'Opacification',
  'Pneumonia',
  'Edema',
  'Fibrosis',
  'Mediastinum',
  'Hilum',
]

function TermCard({ data }) {
  const [speaking, setSpeaking] = useState(false)

  const handleSpeak = () => {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel()
      const utterance = new SpeechSynthesisUtterance(
        `${data.term}. ${data.definition}. ${data.why_it_matters}`
      )
      utterance.rate = 0.9
      utterance.onend = () => setSpeaking(false)
      setSpeaking(true)
      window.speechSynthesis.speak(utterance)
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 24, scale: 0.97 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.5, ease: 'easeOut' }}
    >
      <div className="bg-slate-900/60 rounded-3xl border border-slate-700/50 overflow-hidden
                      shadow-xl shadow-emerald-500/5">
        {/* Term header */}
        <div className="bg-gradient-to-r from-emerald-500/10 via-teal-500/10 to-cyan-500/10 
                        border-b border-slate-700/40 px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-xl font-bold text-white tracking-tight">{data.term}</h3>
              {data.pronunciation && (
                <p className="text-sm text-emerald-400/80 mt-0.5 font-mono">
                  /{data.pronunciation}/
                </p>
              )}
            </div>
            <button
              onClick={handleSpeak}
              className={`w-10 h-10 rounded-xl flex items-center justify-center transition-all
                         ${speaking 
                           ? 'bg-emerald-500 text-white shadow-lg shadow-emerald-500/30' 
                           : 'bg-slate-800 text-slate-400 hover:bg-emerald-500/20 hover:text-emerald-400 border border-slate-700'}`}
              title="Listen to pronunciation"
            >
              <Volume2 size={18} className={speaking ? 'animate-pulse' : ''} />
            </button>
          </div>
        </div>

        {/* Content sections */}
        <div className="p-6 space-y-5">
          {/* Definition */}
          <motion.div
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.1 }}
          >
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-lg bg-sky-500/10 border border-sky-500/20 
                              flex items-center justify-center shrink-0 mt-0.5">
                <BookHeart size={15} className="text-sky-400" />
              </div>
              <div>
                <h4 className="text-[11px] font-bold text-sky-400 uppercase tracking-wider mb-1">
                  What it means
                </h4>
                <p className="text-sm text-slate-300 leading-relaxed">
                  {data.definition}
                </p>
              </div>
            </div>
          </motion.div>

          {/* Why it matters */}
          {data.why_it_matters && (
            <motion.div
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.2 }}
            >
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-amber-500/10 border border-amber-500/20 
                                flex items-center justify-center shrink-0 mt-0.5">
                  <HeartPulse size={15} className="text-amber-400" />
                </div>
                <div>
                  <h4 className="text-[11px] font-bold text-amber-400 uppercase tracking-wider mb-1">
                    Why it matters
                  </h4>
                  <p className="text-sm text-slate-300 leading-relaxed">
                    {data.why_it_matters}
                  </p>
                </div>
              </div>
            </motion.div>
          )}

          {/* Analogy */}
          {data.analogy && (
            <motion.div
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.3 }}
            >
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-violet-500/10 border border-violet-500/20 
                                flex items-center justify-center shrink-0 mt-0.5">
                  <Lightbulb size={15} className="text-violet-400" />
                </div>
                <div>
                  <h4 className="text-[11px] font-bold text-violet-400 uppercase tracking-wider mb-1">
                    Think of it like…
                  </h4>
                  <p className="text-sm text-slate-300 leading-relaxed italic">
                    "{data.analogy}"
                  </p>
                </div>
              </div>
            </motion.div>
          )}

          {/* Related terms */}
          {data.related_terms?.length > 0 && (
            <motion.div
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.4 }}
            >
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20 
                                flex items-center justify-center shrink-0 mt-0.5">
                  <Link2 size={15} className="text-emerald-400" />
                </div>
                <div>
                  <h4 className="text-[11px] font-bold text-emerald-400 uppercase tracking-wider mb-1.5">
                    Related terms
                  </h4>
                  <div className="flex flex-wrap gap-2">
                    {data.related_terms.map((rt) => (
                      <span
                        key={rt}
                        className="text-xs text-emerald-300 bg-emerald-500/10 border border-emerald-500/20
                                   px-3 py-1 rounded-full"
                      >
                        {rt}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </motion.div>
          )}
        </div>
      </div>
    </motion.div>
  )
}

export default function MedicalTermLookup() {
  const [term, setTerm] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [history, setHistory] = useState([])
  const inputRef = useRef(null)

  const handleLookup = async (searchTerm) => {
    const t = (searchTerm || term).trim()
    if (!t) return

    setLoading(true)
    setError(null)

    try {
      const res = await fetch('/explain-term', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ term: t }),
      })
      const data = await res.json()
      if (data.error) throw new Error(data.error)
      setResult(data)
      // Add to history (avoid duplicates)
      setHistory(prev => {
        const filtered = prev.filter(h => h.toLowerCase() !== t.toLowerCase())
        return [t, ...filtered].slice(0, 10)
      })
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = (e) => {
    e?.preventDefault()
    handleLookup()
  }

  const handleTermClick = (t) => {
    setTerm(t)
    handleLookup(t)
  }

  return (
    <div className="max-w-4xl mx-auto">
      <div className="glass rounded-3xl p-6 glow-emerald relative overflow-hidden">
        {/* Decorative background gradient */}
        <div className="absolute -top-20 -right-20 w-60 h-60 bg-emerald-500/5 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute -bottom-20 -left-20 w-60 h-60 bg-teal-500/5 rounded-full blur-3xl pointer-events-none" />

        {/* Header */}
        <div className="relative flex items-center justify-between mb-1">
          <h3 className="text-lg font-semibold flex items-center gap-2">
            <span className="bg-gradient-to-r from-emerald-400 to-teal-400 bg-clip-text text-transparent">
              🩺 Medical Term Lookup
            </span>
          </h3>
          <span className="text-[10px] text-slate-600 bg-slate-800 px-2 py-0.5 rounded-full flex items-center gap-1">
            <Sparkles size={9} /> Powered by AI
          </span>
        </div>
        <p className="text-xs text-slate-500 mb-5 relative">
          Don't understand a medical term in your report? Type it here and get a simple, patient-friendly explanation.
        </p>

        {/* Search bar */}
        <form onSubmit={handleSubmit} className="relative">
          <div className="relative">
            <HelpCircle size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500" />
            <input
              ref={inputRef}
              type="text"
              value={term}
              onChange={(e) => setTerm(e.target.value)}
              placeholder="Type any medical term… e.g. Cardiomegaly, Pleural Effusion"
              className="w-full bg-slate-900/80 border border-slate-700 rounded-2xl pl-11 pr-28 py-3.5 text-sm text-slate-200
                         placeholder:text-slate-600 focus:outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20 transition-all"
            />
            <button
              type="submit"
              disabled={loading || !term.trim()}
              className="absolute right-2 top-1/2 -translate-y-1/2
                         px-4 py-2 bg-gradient-to-r from-emerald-500 to-teal-500 rounded-xl text-xs font-semibold text-white
                         hover:from-emerald-400 hover:to-teal-400 disabled:opacity-40 disabled:cursor-not-allowed
                         transition-all flex items-center gap-1.5 shadow-lg shadow-emerald-500/20"
            >
              {loading ? <Loader2 size={13} className="animate-spin" /> : <ArrowRight size={13} />}
              Explain
            </button>
          </div>
        </form>

        {/* Common terms pills */}
        {!result && !loading && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="mt-4"
          >
            <span className="text-[10px] text-slate-600 mb-2 block">Common terms patients ask about:</span>
            <div className="flex flex-wrap gap-2">
              {COMMON_TERMS.map((t) => (
                <button
                  key={t}
                  onClick={() => handleTermClick(t)}
                  className="text-[11px] text-slate-400 bg-slate-800/60 hover:bg-emerald-500/10 hover:text-emerald-400
                             border border-slate-700/50 hover:border-emerald-500/30
                             px-3 py-1.5 rounded-full transition-all duration-200"
                >
                  {t}
                </button>
              ))}
            </div>
          </motion.div>
        )}

        {/* Loading state */}
        <AnimatePresence>
          {loading && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="mt-6 flex flex-col items-center gap-3 py-8"
            >
              <div className="relative">
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
                  className="w-12 h-12 rounded-full border-2 border-emerald-500/20 border-t-emerald-400"
                />
                <BookHeart size={18} className="absolute inset-0 m-auto text-emerald-400" />
              </div>
              <p className="text-xs text-slate-500">Looking up "{term}"…</p>
              <p className="text-[10px] text-slate-600">Our AI is preparing a simple explanation for you</p>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Error */}
        {error && (
          <div className="mt-4 text-xs text-red-400 bg-red-500/10 rounded-xl px-4 py-3 border border-red-500/20">
            ⚠️ {error}
          </div>
        )}

        {/* Result */}
        <AnimatePresence>
          {result && !loading && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="mt-6"
            >
              {/* Clear button */}
              <div className="flex justify-end mb-3">
                <button
                  onClick={() => { setResult(null); setTerm(''); inputRef.current?.focus() }}
                  className="text-[11px] text-slate-500 hover:text-slate-300 transition-colors flex items-center gap-1"
                >
                  <X size={12} /> Clear
                </button>
              </div>
              <TermCard data={result} />
            </motion.div>
          )}
        </AnimatePresence>

        {/* Recent lookups */}
        {history.length > 0 && !loading && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="mt-5 pt-4 border-t border-slate-800/60"
          >
            <span className="text-[10px] text-slate-600 mb-2 block">Recent lookups:</span>
            <div className="flex flex-wrap gap-2">
              {history.map((h) => (
                <button
                  key={h}
                  onClick={() => handleTermClick(h)}
                  className="text-[11px] text-teal-400/80 bg-teal-500/5 hover:bg-teal-500/10
                             border border-teal-500/10 hover:border-teal-500/30
                             px-3 py-1 rounded-full transition-all duration-200 flex items-center gap-1"
                >
                  <Search size={9} /> {h}
                </button>
              ))}
            </div>
          </motion.div>
        )}

        {/* Disclaimer */}
        <div className="mt-5 bg-slate-800/30 rounded-xl px-4 py-3 border border-slate-700/30 relative">
          <p className="text-[10px] text-slate-600 leading-relaxed flex items-start gap-2">
            <HelpCircle size={11} className="mt-0.5 shrink-0 text-slate-500" />
            <span>
              Explanations are generated by AI to help you understand medical terminology. 
              They are simplified for general understanding and should not replace professional medical advice. 
              Always discuss your results with your healthcare provider.
            </span>
          </p>
        </div>
      </div>
    </div>
  )
}
