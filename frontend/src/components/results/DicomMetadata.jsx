import { Scan } from 'lucide-react'

const TAGS = [
  ['PatientAge', 'Age'], ['PatientSex', 'Sex'], ['StudyDate', 'Study Date'],
  ['Modality', 'Modality'], ['ViewPosition', 'View'], ['BodyPartExamined', 'Body Part'],
  ['InstitutionName', 'Institution'], ['ReferringPhysicianName', 'Physician'],
  ['PixelSpacing', 'Pixel Spacing'], ['KVP', 'kVp'], ['Exposure', 'Exposure'],
]

export default function DicomMetadata({ metadata }) {
  const entries = TAGS.filter(([key]) => metadata[key])
  if (entries.length === 0) return null

  return (
    <div className="glass rounded-2xl p-5 border-l-4 border-indigo-500">
      <h3 className="text-sm font-semibold text-indigo-400 flex items-center gap-2 mb-4">
        <Scan size={16} /> DICOM Metadata
      </h3>
      <div className="bg-slate-900/60 rounded-xl overflow-hidden divide-y divide-slate-800">
        {entries.map(([key, label]) => {
          let val = metadata[key]
          if (Array.isArray(val)) val = val.join(' × ')
          return (
            <div key={key} className="flex justify-between px-3 py-2 text-xs">
              <span className="text-slate-500">{label}</span>
              <span className="text-slate-200 font-medium">{val}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
