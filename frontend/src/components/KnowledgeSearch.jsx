import { useState, useRef } from 'react'
import { Search, BookOpen, Loader2, Image, FileText, Download, ChevronDown, ChevronUp, Sparkles, GraduationCap, Hash, Layers, Eye, BookMarked, Zap } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

const SAMPLE_QUERIES = [
  'Signs of pneumonia on chest X-ray',
  'Cardiomegaly differential diagnosis',
  'Pleural effusion radiographic features',
  'Pneumothorax identification',
  'Tuberculosis X-ray findings',
]

function RelevanceMeter({ score }) {
  const pct = (score * 100).toFixed(0)
  const color = score > 0.7 ? 'from-emerald-500 to-emerald-400' :
                score > 0.4 ? 'from-amber-500 to-yellow-400' :
                'from-sky-500 to-indigo-400'
  const label = score > 0.7 ? 'High' : score > 0.4 ? 'Medium' : 'Low'
  const labelColor = score > 0.7 ? 'text-emerald-400' : score > 0.4 ? 'text-amber-400' : 'text-sky-400'

  return (
    <div className="flex items-center gap-2 min-w-[120px]">
      <div className="flex-1 h-1.5 bg-slate-800 rounded-full overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
          className={`h-full rounded-full bg-gradient-to-r ${color}`}
        />
      </div>
      <span className={`text-[10px] font-bold ${labelColor} min-w-[32px]`}>{pct}%</span>
    </div>
  )
}

function TextResult({ result, index, isExpanded, onToggle }) {
  const content = result.content || ''
  const isLong = content.length > 200
  const displayContent = isExpanded ? content : content.slice(0, 200)

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.08, duration: 0.4 }}
      className="group"
    >
      <div className="bg-slate-900/50 rounded-2xl border border-slate-700/50 hover:border-sky-500/20 
                      transition-all duration-300 overflow-hidden">
        {/* Header */}
        <div className="px-4 py-3 flex items-start justify-between gap-3 border-b border-slate-800/60">
          <div className="flex items-start gap-3 flex-1 min-w-0">
            <div className="w-8 h-8 rounded-lg bg-sky-500/10 border border-sky-500/20 
                            flex items-center justify-center shrink-0 mt-0.5">
              <FileText size={14} className="text-sky-400" />
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2 flex-wrap">
                {result.title && (
                  <h4 className="text-xs font-semibold text-slate-200 truncate">{result.title}</h4>
                )}
                {result.author && result.author !== 'Unknown' && (
                  <span className="text-[10px] text-slate-600">by {result.author}</span>
                )}
              </div>
              <div className="flex items-center gap-2 mt-0.5 flex-wrap">
                {result.chunk_index != null && result.total_chunks && (
                  <span className="inline-flex items-center gap-1 text-[10px] text-slate-600">
                    <Layers size={9} /> Section {result.chunk_index + 1} of {result.total_chunks}
                  </span>
                )}
                <span className="inline-flex items-center gap-1 text-[10px] text-indigo-400/70">
                  <Hash size={9} /> Result #{index + 1}
                </span>
              </div>
            </div>
          </div>
          <RelevanceMeter score={result.score} />
        </div>

        {/* Content */}
        <div className="px-4 py-3">
          <p className="text-[13px] text-slate-300 leading-relaxed whitespace-pre-wrap">
            {displayContent}{isLong && !isExpanded && '…'}
          </p>
          {isLong && (
            <button
              onClick={onToggle}
              className="mt-2 flex items-center gap-1 text-[11px] text-sky-400 hover:text-sky-300 transition-colors"
            >
              {isExpanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
              {isExpanded ? 'Show less' : 'Read full excerpt'}
            </button>
          )}
        </div>
      </div>
    </motion.div>
  )
}

function ImageResult({ result, index }) {
  const [showFull, setShowFull] = useState(false)

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.08, duration: 0.4 }}
    >
      <div className="bg-slate-900/50 rounded-2xl border border-slate-700/50 hover:border-indigo-500/20 
                      transition-all duration-300 overflow-hidden">
        {/* Header */}
        <div className="px-4 py-3 flex items-center justify-between border-b border-slate-800/60">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-indigo-500/10 border border-indigo-500/20 
                            flex items-center justify-center">
              <Image size={14} className="text-indigo-400" />
            </div>
            <div>
              <h4 className="text-xs font-semibold text-slate-200 flex items-center gap-1.5">
                <BookMarked size={11} className="text-indigo-400" />
                {result.title || result.filename || 'Book Image'}
              </h4>
              {result.page_number && (
                <span className="text-[10px] text-indigo-400/70">📄 Page {result.page_number}</span>
              )}
            </div>
          </div>
          <RelevanceMeter score={result.score} />
        </div>

        {/* Content */}
        <div className="p-4">
          {result.ocr_text && (
            <p className="text-[13px] text-slate-300 leading-relaxed mb-3 
                          bg-slate-800/40 rounded-xl px-3 py-2 border-l-2 border-indigo-500/30">
              {result.ocr_text}
            </p>
          )}
          {result.image_data && (
            <div className="relative">
              <img
                src={`data:image/png;base64,${result.image_data}`}
                alt={`Book page ${result.page_number || ''}`}
                className={`rounded-xl border border-slate-700 cursor-pointer transition-all duration-300
                           ${showFull ? 'max-h-none' : 'max-h-56 object-cover'} w-full`}
                onClick={() => setShowFull(!showFull)}
              />
              {!showFull && (
                <div className="absolute inset-x-0 bottom-0 h-16 bg-gradient-to-t from-slate-900/90 to-transparent 
                                rounded-b-xl flex items-end justify-center pb-2">
                  <button
                    onClick={() => setShowFull(true)}
                    className="flex items-center gap-1 text-[11px] text-sky-400 hover:text-sky-300 
                               bg-slate-900/80 backdrop-blur px-3 py-1 rounded-full border border-sky-500/20"
                  >
                    <Eye size={11} /> View full image
                  </button>
                </div>
              )}
              {showFull && (
                <button
                  onClick={() => setShowFull(false)}
                  className="mt-2 flex items-center gap-1 text-[11px] text-sky-400 hover:text-sky-300"
                >
                  <ChevronUp size={12} /> Collapse
                </button>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        {result.image_data && (
          <div className="px-4 pb-3">
            <a
              href={`data:image/png;base64,${result.image_data}`}
              download={`radiology_reference_page_${result.page_number || 'unknown'}.png`}
              className="inline-flex items-center gap-1.5 text-[11px] text-sky-400 hover:text-sky-300
                         bg-sky-500/10 hover:bg-sky-500/20 border border-sky-500/20 
                         rounded-lg px-3 py-1.5 transition-all"
            >
              <Download size={11} /> Download Image
            </a>
          </div>
        )}
      </div>
    </motion.div>
  )
}

export default function KnowledgeSearch() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [expandedCards, setExpandedCards] = useState({})
  const inputRef = useRef(null)

  const toggleExpand = (idx) => {
    setExpandedCards(prev => ({ ...prev, [idx]: !prev[idx] }))
  }

  const handleSearch = async (e) => {
    e?.preventDefault()
    const q = query.trim()
    if (!q) return

    setLoading(true)
    setError(null)
    setExpandedCards({})

    try {
      const res = await fetch('/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: q }),
      })
      const data = await res.json()
      if (data.error) throw new Error(data.error)
      setResults(data.results || [])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleSampleClick = (sample) => {
    setQuery(sample)
    setTimeout(() => {
      const fakeEvent = { preventDefault: () => {} }
      setQuery(sample)
      handleSearchDirect(sample)
    }, 100)
  }

  const handleSearchDirect = async (q) => {
    if (!q.trim()) return
    setLoading(true)
    setError(null)
    setExpandedCards({})
    try {
      const res = await fetch('/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: q.trim() }),
      })
      const data = await res.json()
      if (data.error) throw new Error(data.error)
      setResults(data.results || [])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const textResults = results?.filter(r => r.type === 'text') || []
  const imageResults = results?.filter(r => r.type === 'image') || []

  return (
    <div className="max-w-4xl mx-auto">
      <div className="glass rounded-3xl p-6 glow-sky">
        {/* Header */}
        <div className="flex items-center justify-between mb-1">
          <h3 className="text-lg font-semibold gradient-text flex items-center gap-2">
            <GraduationCap size={20} /> Radiology Knowledge Base
          </h3>
          <span className="text-[10px] text-slate-600 bg-slate-800 px-2 py-0.5 rounded-full">
            Powered by RAG + Pinecone
          </span>
        </div>
        <p className="text-xs text-slate-500 mb-5">
          Search our indexed radiology textbook for clinical references, diagnostic criteria, and imaging guidelines.
        </p>

        {/* Search bar */}
        <form onSubmit={handleSearch} className="relative">
          <div className="relative">
            <Search size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500" />
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Ask a radiology question..."
              className="w-full bg-slate-900/80 border border-slate-700 rounded-2xl pl-11 pr-24 py-3.5 text-sm text-slate-200
                         placeholder:text-slate-600 focus:outline-none focus:border-sky-500 focus:ring-2 focus:ring-sky-500/20 transition-all"
            />
            <button
              type="submit"
              disabled={loading || !query.trim()}
              className="absolute right-2 top-1/2 -translate-y-1/2
                         px-4 py-2 bg-gradient-to-r from-sky-500 to-indigo-500 rounded-xl text-xs font-semibold text-white
                         hover:from-sky-400 hover:to-indigo-400 disabled:opacity-40 disabled:cursor-not-allowed
                         transition-all flex items-center gap-1.5 shadow-lg shadow-sky-500/20"
            >
              {loading ? <Loader2 size={13} className="animate-spin" /> : <Zap size={13} />}
              Search
            </button>
          </div>
        </form>

        {/* Sample queries */}
        {!results && !loading && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="mt-4 flex flex-wrap gap-2"
          >
            <span className="text-[10px] text-slate-600 self-center mr-1">Try:</span>
            {SAMPLE_QUERIES.map((sq) => (
              <button
                key={sq}
                onClick={() => handleSampleClick(sq)}
                className="text-[11px] text-slate-400 bg-slate-800/60 hover:bg-slate-800 hover:text-sky-400
                           border border-slate-700/50 hover:border-sky-500/30
                           px-3 py-1.5 rounded-full transition-all duration-200"
              >
                {sq}
              </button>
            ))}
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
                  className="w-12 h-12 rounded-full border-2 border-sky-500/20 border-t-sky-400"
                />
                <BookOpen size={18} className="absolute inset-0 m-auto text-sky-400" />
              </div>
              <p className="text-xs text-slate-500">Searching knowledge base…</p>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Error */}
        {error && (
          <div className="mt-4 text-xs text-red-400 bg-red-500/10 rounded-xl px-4 py-3 border border-red-500/20">
            ⚠️ {error}
          </div>
        )}

        {/* Results */}
        <AnimatePresence>
          {results && !loading && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="mt-6"
            >
              {results.length > 0 ? (
                <>
                  {/* Results summary */}
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-2">
                      <Sparkles size={14} className="text-sky-400" />
                      <span className="text-xs text-slate-400">
                        Found <strong className="text-sky-400">{results.length}</strong> results
                      </span>
                      {textResults.length > 0 && (
                        <span className="text-[10px] text-slate-600 bg-slate-800 px-2 py-0.5 rounded-full">
                          📝 {textResults.length} text
                        </span>
                      )}
                      {imageResults.length > 0 && (
                        <span className="text-[10px] text-slate-600 bg-slate-800 px-2 py-0.5 rounded-full">
                          🖼 {imageResults.length} images
                        </span>
                      )}
                    </div>
                    <button
                      onClick={() => { setResults(null); setQuery(''); inputRef.current?.focus() }}
                      className="text-[11px] text-slate-500 hover:text-slate-300 transition-colors"
                    >
                      Clear results
                    </button>
                  </div>

                  {/* Text results */}
                  {textResults.length > 0 && (
                    <div className="space-y-3 mb-4">
                      {textResults.map((r, i) => (
                        <TextResult
                          key={`text-${i}`}
                          result={r}
                          index={i}
                          isExpanded={!!expandedCards[`text-${i}`]}
                          onToggle={() => toggleExpand(`text-${i}`)}
                        />
                      ))}
                    </div>
                  )}

                  {/* Image results */}
                  {imageResults.length > 0 && (
                    <>
                      {textResults.length > 0 && (
                        <div className="flex items-center gap-2 my-4">
                          <div className="flex-1 h-px bg-slate-800" />
                          <span className="text-[10px] text-slate-600 flex items-center gap-1">
                            <Image size={10} /> Visual References
                          </span>
                          <div className="flex-1 h-px bg-slate-800" />
                        </div>
                      )}
                      <div className="space-y-3">
                        {imageResults.map((r, i) => (
                          <ImageResult key={`img-${i}`} result={r} index={i + textResults.length} />
                        ))}
                      </div>
                    </>
                  )}

                  {/* Source attribution */}
                  <div className="mt-5 bg-slate-800/30 rounded-xl px-4 py-3 border border-slate-700/30">
                    <p className="text-[10px] text-slate-600 leading-relaxed flex items-start gap-2">
                      <BookOpen size={11} className="mt-0.5 shrink-0 text-slate-500" />
                      <span>
                        Results sourced from indexed radiology textbooks using semantic vector search.
                        Content is retrieved from the nearest embedding matches in our Pinecone knowledge base.
                        Always verify clinical information with primary sources.
                      </span>
                    </p>
                  </div>
                </>
              ) : (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="text-center py-8"
                >
                  <div className="w-14 h-14 mx-auto rounded-2xl bg-slate-800/60 flex items-center justify-center mb-3">
                    <Search size={24} className="text-slate-600" />
                  </div>
                  <p className="text-sm text-slate-500 font-medium">No matching results</p>
                  <p className="text-xs text-slate-600 mt-1">
                    Try rephrasing your question or using different keywords.
                  </p>
                </motion.div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}
