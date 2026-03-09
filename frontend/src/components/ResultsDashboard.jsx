import { Component } from 'react'
import { motion } from 'framer-motion'
import QualityReport from './results/QualityReport'
import EnhancedComparison from './results/EnhancedComparison'
import SegmentationCTR from './results/SegmentationCTR'
import UncertaintyCard from './results/UncertaintyCard'
import GradCAMCard from './results/GradCAMCard'
import DetectionsCard from './results/DetectionsCard'
import DifferentialsCard from './results/DifferentialsCard'
import ClinicalDecision from './results/ClinicalDecision'
import DiagnosisReport from './results/DiagnosisReport'
import DicomMetadata from './results/DicomMetadata'

const fadeUp = {
  hidden: { opacity: 0, y: 30 },
  visible: (i) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.1, duration: 0.5, ease: 'easeOut' },
  }),
}

/* React Error Boundary — catches crashes in child components */
class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }
  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }
  componentDidCatch(error, info) {
    console.error(`[ErrorBoundary] ${this.props.label}:`, error, info)
  }
  render() {
    if (this.state.hasError) {
      return (
        <div className="glass rounded-2xl p-5 border border-red-500/20">
          <p className="text-xs text-red-400">
            ⚠️ Error rendering {this.props.label}: {this.state.error?.message}
          </p>
        </div>
      )
    }
    return this.props.children
  }
}

export default function ResultsDashboard({ data }) {
  if (!data) return null

  console.log('📊 ResultsDashboard data keys:', Object.keys(data))

  // Calculate row indices upfront  
  const rows = []
  let idx = 0

  // Success banner — always
  rows.push({ key: 'banner', idx: idx++ })

  // Quality/DICOM
  if (data.quality_report || (data.dicom_metadata && Object.keys(data.dicom_metadata).length > 0)) {
    rows.push({ key: 'quality', idx: idx++ })
  }

  // Enhancement
  if (data.enhanced_comparison) rows.push({ key: 'enhancement', idx: idx++ })

  // Segmentation
  if (data.segmentation_overlay || data.ctr) rows.push({ key: 'segmentation', idx: idx++ })

  // Uncertainty
  if (data.uncertainty && Object.keys(data.uncertainty).length > 0) rows.push({ key: 'uncertainty', idx: idx++ })

  // Grad-CAM or Detections
  if (data.heatmap) rows.push({ key: 'gradcam', idx: idx++ })
  else if (data.detections?.length > 0) rows.push({ key: 'detections', idx: idx++ })

  // Differentials
  if (data.differentials?.length > 0) rows.push({ key: 'differentials', idx: idx++ })

  // Clinical Decision
  if (data.clinical_decision && Object.keys(data.clinical_decision).length > 0) rows.push({ key: 'clinical', idx: idx++ })

  // Diagnosis Report
  if (data.diagnosis) rows.push({ key: 'diagnosis', idx: idx++ })

  // Image fallback
  if (data.image_path && !data.heatmap && !data.segmentation_overlay && !data.enhanced_comparison) {
    rows.push({ key: 'image', idx: idx++ })
  }

  const getIdx = (key) => rows.find(r => r.key === key)?.idx ?? 0

  return (
    <motion.div
      className="space-y-5"
      initial="hidden"
      animate="visible"
    >
      {/* Success banner */}
      <motion.div
        custom={getIdx('banner')}
        variants={fadeUp}
        className="glass rounded-2xl p-4 border border-emerald-500/30 bg-emerald-500/5
                   flex items-center gap-3"
      >
        <div className="w-10 h-10 rounded-xl bg-emerald-500/20 flex items-center justify-center text-lg">
          ✅
        </div>
        <div>
          <p className="text-sm font-semibold text-emerald-400">Analysis Complete</p>
          <p className="text-xs text-slate-500">
            {data.image_path ? data.image_path.split('/').pop() : 'Image'} — {' '}
            {data.detections?.length || 0} pathologies evaluated
            {data.severity && <span className="ml-1">• Severity: <span className="text-slate-300 font-medium">{data.severity}</span></span>}
          </p>
        </div>
      </motion.div>

      {/* Row 1: Quality + DICOM */}
      {(data.quality_report || (data.dicom_metadata && Object.keys(data.dicom_metadata).length > 0)) && (
        <motion.div custom={getIdx('quality')} variants={fadeUp} className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          {data.quality_report && (
            <ErrorBoundary label="Quality Report">
              <QualityReport report={data.quality_report} />
            </ErrorBoundary>
          )}
          {data.dicom_metadata && Object.keys(data.dicom_metadata).length > 0 && (
            <ErrorBoundary label="DICOM Metadata">
              <DicomMetadata metadata={data.dicom_metadata} />
            </ErrorBoundary>
          )}
        </motion.div>
      )}

      {/* Row 2: Enhancement */}
      {data.enhanced_comparison && (
        <motion.div custom={getIdx('enhancement')} variants={fadeUp}>
          <ErrorBoundary label="Enhanced Comparison">
            <EnhancedComparison imageB64={data.enhanced_comparison} />
          </ErrorBoundary>
        </motion.div>
      )}

      {/* Row 3: Segmentation + CTR */}
      {(data.segmentation_overlay || data.ctr) && (
        <motion.div custom={getIdx('segmentation')} variants={fadeUp}>
          <ErrorBoundary label="Segmentation">
            <SegmentationCTR
              overlay={data.segmentation_overlay}
              ctr={data.ctr}
              measurements={data.measurements}
            />
          </ErrorBoundary>
        </motion.div>
      )}

      {/* Row 4: Uncertainty */}
      {data.uncertainty && Object.keys(data.uncertainty).length > 0 && (
        <motion.div custom={getIdx('uncertainty')} variants={fadeUp}>
          <ErrorBoundary label="Uncertainty">
            <UncertaintyCard uncertainty={data.uncertainty} />
          </ErrorBoundary>
        </motion.div>
      )}

      {/* Row 5: Grad-CAM or Detections */}
      {data.heatmap ? (
        <motion.div custom={getIdx('gradcam')} variants={fadeUp}>
          <ErrorBoundary label="Grad-CAM">
            <GradCAMCard heatmap={data.heatmap} detections={data.detections} />
          </ErrorBoundary>
        </motion.div>
      ) : data.detections?.length > 0 ? (
        <motion.div custom={getIdx('detections')} variants={fadeUp}>
          <ErrorBoundary label="Detections">
            <DetectionsCard detections={data.detections} />
          </ErrorBoundary>
        </motion.div>
      ) : null}

      {/* Row 6: Differentials */}
      {data.differentials?.length > 0 && (
        <motion.div custom={getIdx('differentials')} variants={fadeUp}>
          <ErrorBoundary label="Differentials">
            <DifferentialsCard differentials={data.differentials} />
          </ErrorBoundary>
        </motion.div>
      )}

      {/* Row 7: Clinical Decision */}
      {data.clinical_decision && Object.keys(data.clinical_decision).length > 0 && (
        <motion.div custom={getIdx('clinical')} variants={fadeUp}>
          <ErrorBoundary label="Clinical Decision">
            <ClinicalDecision decision={data.clinical_decision} />
          </ErrorBoundary>
        </motion.div>
      )}

      {/* Row 8: Diagnosis Report */}
      {data.diagnosis && (
        <motion.div custom={getIdx('diagnosis')} variants={fadeUp}>
          <ErrorBoundary label="Diagnosis Report">
            <DiagnosisReport
              diagnosis={data.diagnosis}
              severity={data.severity}
              language={data.language}
            />
          </ErrorBoundary>
        </motion.div>
      )}

      {/* Original image fallback */}
      {data.image_path && !data.heatmap && !data.segmentation_overlay && !data.enhanced_comparison && (
        <motion.div custom={getIdx('image')} variants={fadeUp} className="glass rounded-2xl p-6 text-center">
          <h3 className="text-sm font-semibold text-slate-400 mb-3">📷 Uploaded X-ray</h3>
          <img src={data.image_path} alt="X-ray" className="max-h-96 mx-auto rounded-xl border border-slate-700" />
        </motion.div>
      )}
    </motion.div>
  )
}
