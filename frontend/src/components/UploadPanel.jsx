import { useState, useRef } from 'react'
import { Upload, User, Globe, Cigarette, Shield, Building2, Loader2, Scan, Zap, Brain, Activity } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

const LANGUAGES = [
  { code: 'en', flag: '🇬🇧', name: 'English' },
  { code: 'ar', flag: '🇸🇦', name: 'العربية' },
  { code: 'ur', flag: '🇵🇰', name: 'اردو' },
  { code: 'hi', flag: '🇮🇳', name: 'हिन्दी' },
  { code: 'es', flag: '🇪🇸', name: 'Español' },
  { code: 'fr', flag: '🇫🇷', name: 'Français' },
  { code: 'de', flag: '🇩🇪', name: 'Deutsch' },
  { code: 'zh', flag: '🇨🇳', name: '中文' },
  { code: 'pt', flag: '🇧🇷', name: 'Português' },
  { code: 'tr', flag: '🇹🇷', name: 'Türkçe' },
  { code: 'ru', flag: '🇷🇺', name: 'Русский' },
]

export default function UploadPanel({ onUpload, isAnalyzing }) {
  const [dragOver, setDragOver] = useState(false)
  const [preview, setPreview] = useState(null)
  const [fileName, setFileName] = useState('')
  const fileRef = useRef(null)

  const handleFile = (file) => {
    if (!file) return
    setFileName(file.name)
    if (file.type.startsWith('image/')) {
      const reader = new FileReader()
      reader.onload = (e) => setPreview(e.target.result)
      reader.readAsDataURL(file)
    } else {
      setPreview(null)
    }
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer.files[0]
    if (file) {
      const dt = new DataTransfer()
      dt.items.add(file)
      fileRef.current.files = dt.files
      handleFile(file)
    }
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    const file = fileRef.current?.files[0]
    if (!file) return

    const formData = new FormData()
    formData.append('file', file)

    const form = e.target
    const age = form.patient_age?.value
    const sex = form.patient_sex?.value
    const symptoms = form.patient_symptoms?.value
    const duration = form.symptom_duration?.value
    const smoking = form.smoking?.checked
    const immuno = form.immunocompromised?.checked
    const comorbid = form.comorbidities?.checked
    const language = form.language?.value || 'en'

    if (age) formData.append('patient_age', age)
    if (sex) formData.append('patient_sex', sex)
    if (symptoms) formData.append('patient_symptoms', symptoms)
    if (duration) formData.append('symptom_duration', duration)
    if (smoking) formData.append('smoking', 'true')
    if (immuno) formData.append('immunocompromised', 'true')
    if (comorbid) formData.append('comorbidities', 'true')
    formData.append('language', language)

    onUpload(formData)
  }

  return (
    <form onSubmit={handleSubmit}>
      <div className="glass rounded-3xl p-6 sm:p-8 glow-sky">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Left: File Upload */}
          <div>
            <h3 className="text-lg font-semibold text-sky-400 flex items-center gap-2 mb-4">
              <Upload size={20} /> Upload Medical Image
            </h3>

            <div
              className={`relative border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition-all duration-300
                ${dragOver
                  ? 'border-sky-400 bg-sky-400/10 scale-[1.02]'
                  : 'border-slate-600 hover:border-slate-500 hover:bg-slate-800/30'
                }`}
              onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleDrop}
              onClick={() => fileRef.current?.click()}
            >
              <input
                ref={fileRef}
                type="file"
                accept="image/*,.dcm,.dicom,.pdf"
                className="hidden"
                onChange={(e) => handleFile(e.target.files[0])}
              />

              {preview ? (
                <div className="space-y-3">
                  <img src={preview} alt="Preview" className="max-h-48 mx-auto rounded-xl border border-slate-700" />
                  <p className="text-sm text-slate-400">{fileName}</p>
                  <p className="text-xs text-sky-400">Click or drop to change</p>
                </div>
              ) : (
                <div className="space-y-3">
                  <div className="w-16 h-16 mx-auto rounded-2xl bg-slate-800 flex items-center justify-center">
                    <Upload size={28} className="text-slate-500" />
                  </div>
                  <div>
                    <p className="text-slate-300 font-medium">
                      {fileName || 'Drop your X-ray image here'}
                    </p>
                    <p className="text-xs text-slate-500 mt-1">
                      PNG, JPG, DICOM (.dcm), or PDF — Max 32MB
                    </p>
                  </div>
                </div>
              )}
            </div>

            {/* Language */}
            <div className="mt-4">
              <label className="text-xs text-slate-400 font-medium flex items-center gap-1 mb-1.5">
                <Globe size={12} /> Report Language
              </label>
              <select
                name="language"
                defaultValue="en"
                className="w-full bg-slate-900/80 border border-slate-700 rounded-xl px-3 py-2.5 text-sm text-slate-200
                           focus:outline-none focus:border-sky-500 focus:ring-1 focus:ring-sky-500/30 transition-colors"
              >
                {LANGUAGES.map(l => (
                  <option key={l.code} value={l.code}>{l.flag} {l.name}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Right: Patient Context */}
          <div>
            <h3 className="text-lg font-semibold text-indigo-400 flex items-center gap-2 mb-4">
              <User size={20} /> Patient Context
              <span className="text-xs text-slate-500 font-normal">(optional — improves diagnosis)</span>
            </h3>

            <div className="space-y-3">
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="text-xs text-slate-500 mb-1 block">Age</label>
                  <input
                    name="patient_age"
                    type="number"
                    min="0"
                    max="120"
                    placeholder="—"
                    className="w-full bg-slate-900/80 border border-slate-700 rounded-xl px-3 py-2.5 text-sm text-slate-200
                               focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/30 transition-colors"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-500 mb-1 block">Sex</label>
                  <select
                    name="patient_sex"
                    defaultValue=""
                    className="w-full bg-slate-900/80 border border-slate-700 rounded-xl px-3 py-2.5 text-sm text-slate-200
                               focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/30 transition-colors"
                  >
                    <option value="">—</option>
                    <option value="M">Male</option>
                    <option value="F">Female</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs text-slate-500 mb-1 block">Duration</label>
                  <input
                    name="symptom_duration"
                    type="text"
                    placeholder="e.g. 3 days"
                    className="w-full bg-slate-900/80 border border-slate-700 rounded-xl px-3 py-2.5 text-sm text-slate-200
                               focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/30 transition-colors"
                  />
                </div>
              </div>

              <div>
                <label className="text-xs text-slate-500 mb-1 block">Symptoms</label>
                <input
                  name="patient_symptoms"
                  type="text"
                  placeholder="e.g. cough, fever, dyspnea, chest pain..."
                  className="w-full bg-slate-900/80 border border-slate-700 rounded-xl px-3 py-2.5 text-sm text-slate-200
                             focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/30 transition-colors"
                />
              </div>

              <div className="flex flex-wrap gap-4 pt-1">
                {[
                  { name: 'smoking', icon: Cigarette, label: 'Smoker', color: 'amber' },
                  { name: 'immunocompromised', icon: Shield, label: 'Immunocompromised', color: 'red' },
                  { name: 'comorbidities', icon: Building2, label: 'Comorbidities', color: 'indigo' },
                ].map(({ name, icon: Icon, label, color }) => (
                  <label key={name} className="flex items-center gap-2 cursor-pointer group">
                    <input
                      type="checkbox"
                      name={name}
                      className={`w-4 h-4 rounded border-slate-600 bg-slate-900
                                  checked:bg-${color}-500 checked:border-${color}-500 transition-colors`}
                    />
                    <Icon size={14} className="text-slate-500 group-hover:text-slate-400 transition-colors" />
                    <span className="text-xs text-slate-400 group-hover:text-slate-300 transition-colors">{label}</span>
                  </label>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Submit */}
        <AnimatePresence mode="wait">
          {isAnalyzing ? (
            <motion.div
              key="analyzing"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="mt-6"
            >
              <div className="relative w-full py-4 rounded-2xl overflow-hidden
                              bg-gradient-to-r from-sky-900/80 via-indigo-900/80 to-violet-900/80
                              border border-sky-500/30 shadow-lg shadow-sky-500/20">
                {/* Animated scanning line */}
                <motion.div
                  className="absolute top-0 left-0 w-full h-full"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                >
                  <motion.div
                    className="absolute top-0 left-0 w-full h-0.5 bg-gradient-to-r from-transparent via-sky-400 to-transparent"
                    animate={{ top: ['0%', '100%', '0%'] }}
                    transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
                  />
                </motion.div>

                {/* Pulsing glow background */}
                <motion.div
                  className="absolute inset-0 bg-sky-500/5"
                  animate={{ opacity: [0, 0.3, 0] }}
                  transition={{ duration: 1.5, repeat: Infinity }}
                />

                <div className="relative flex items-center justify-center gap-3">
                  {/* Animated brain icon */}
                  <motion.div
                    animate={{ rotate: [0, 10, -10, 0], scale: [1, 1.1, 1] }}
                    transition={{ duration: 2, repeat: Infinity }}
                  >
                    <Brain size={20} className="text-sky-400" />
                  </motion.div>

                  {/* Pulsing dots */}
                  <div className="flex items-center gap-1">
                    <span className="text-sm font-semibold text-white">AI Analyzing</span>
                    <motion.span
                      className="text-sky-400 font-bold"
                      animate={{ opacity: [1, 0, 1] }}
                      transition={{ duration: 1.2, repeat: Infinity }}
                    >.</motion.span>
                    <motion.span
                      className="text-sky-400 font-bold"
                      animate={{ opacity: [1, 0, 1] }}
                      transition={{ duration: 1.2, repeat: Infinity, delay: 0.2 }}
                    >.</motion.span>
                    <motion.span
                      className="text-sky-400 font-bold"
                      animate={{ opacity: [1, 0, 1] }}
                      transition={{ duration: 1.2, repeat: Infinity, delay: 0.4 }}
                    >.</motion.span>
                  </div>

                  {/* Spinning activity */}
                  <motion.div
                    animate={{ rotate: 360 }}
                    transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
                  >
                    <Activity size={16} className="text-indigo-400" />
                  </motion.div>
                </div>

                {/* Floating particles */}
                <div className="absolute inset-0 overflow-hidden pointer-events-none">
                  {[...Array(6)].map((_, i) => (
                    <motion.div
                      key={i}
                      className="absolute w-1 h-1 rounded-full bg-sky-400/60"
                      style={{ left: `${15 + i * 14}%` }}
                      animate={{
                        y: [40, -10, 40],
                        opacity: [0, 1, 0],
                        scale: [0.5, 1.2, 0.5],
                      }}
                      transition={{
                        duration: 2 + i * 0.3,
                        repeat: Infinity,
                        delay: i * 0.2,
                      }}
                    />
                  ))}
                </div>
              </div>
            </motion.div>
          ) : (
            <motion.button
              key="submit"
              type="submit"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              whileHover={{ scale: 1.01, y: -2 }}
              whileTap={{ scale: 0.98 }}
              className="mt-6 w-full py-3.5 rounded-2xl font-semibold text-white text-sm
                         bg-gradient-to-r from-sky-500 to-indigo-500 hover:from-sky-400 hover:to-indigo-400
                         shadow-lg shadow-sky-500/20 hover:shadow-sky-500/40
                         transition-all duration-200
                         flex items-center justify-center gap-2 group"
            >
              <motion.div
                className="flex items-center gap-2"
                whileHover={{ x: [0, 2, 0] }}
                transition={{ duration: 0.5, repeat: Infinity }}
              >
                <Zap size={18} className="group-hover:text-yellow-200 transition-colors" />
                <span>Analyze X-ray Image</span>
                <Scan size={16} className="opacity-60" />
              </motion.div>
            </motion.button>
          )}
        </AnimatePresence>
      </div>
    </form>
  )
}
