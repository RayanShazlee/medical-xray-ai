import { Heart } from 'lucide-react'

export default function SegmentationCTR({ overlay, ctr, measurements }) {
  // API returns ctr.ctr (float) not ctr.value
  const ctrRaw = ctr?.ctr ?? ctr?.value ?? null
  const ctrVal = ctrRaw != null ? (ctrRaw * 100).toFixed(1) : null
  const interp = ctr?.interpretation || ctr?.severity || 'N/A'
  const ctrColor = /normal/i.test(interp) ? 'text-emerald-400' : /borderline|mild/i.test(interp) ? 'text-amber-400' : 'text-red-400'
  const ctrBg = /normal/i.test(interp) ? 'bg-emerald-500/15 border-emerald-500/30' : /borderline|mild/i.test(interp) ? 'bg-amber-500/15 border-amber-500/30' : 'bg-red-500/15 border-red-500/30'

  return (
    <div className="glass rounded-2xl p-5">
      <h3 className="text-sm font-semibold text-sky-400 flex items-center gap-2 mb-4">
        🫁 Anatomical Segmentation & CTR
      </h3>
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* Overlay image */}
        {overlay && (
          <div className="lg:col-span-3 flex justify-center">
            <img
              src={`data:image/png;base64,${overlay}`}
              alt="Segmentation"
              className="max-h-[450px] rounded-xl border-2 border-sky-500/30"
            />
          </div>
        )}

        {/* CTR + Measurements */}
        <div className={`${overlay ? 'lg:col-span-2' : 'lg:col-span-5'} flex flex-col items-center justify-center`}>
          {ctrVal && (
            <div className="text-center mb-6">
              <p className="text-xs text-slate-500 uppercase tracking-wider mb-2 flex items-center gap-1 justify-center">
                <Heart size={12} /> Cardiothoracic Ratio
              </p>
              <div className={`text-5xl font-black ${ctrColor} mb-2`}>{ctrVal}%</div>
              <span className={`inline-block px-4 py-1.5 rounded-full text-xs font-bold border ${ctrBg} ${ctrColor}`}>
                {interp}
              </span>
              <p className="text-[10px] text-slate-600 mt-2">Normal: &lt;50% &nbsp;|&nbsp; Borderline: 50-55%</p>
            </div>
          )}

          {measurements && (
            <div className="w-full max-w-xs bg-slate-900/60 rounded-xl divide-y divide-slate-800">
              {measurements.right_lung_area != null && (
                <div className="flex justify-between px-3 py-2 text-xs">
                  <span className="text-slate-500">Right Lung</span>
                  <span className="text-slate-200 font-medium">
                    {typeof measurements.right_lung_area === 'object'
                      ? JSON.stringify(measurements.right_lung_area)
                      : `${measurements.right_lung_area}%`}
                  </span>
                </div>
              )}
              {measurements.left_lung_area != null && (
                <div className="flex justify-between px-3 py-2 text-xs">
                  <span className="text-slate-500">Left Lung</span>
                  <span className="text-slate-200 font-medium">
                    {typeof measurements.left_lung_area === 'object'
                      ? JSON.stringify(measurements.left_lung_area)
                      : `${measurements.left_lung_area}%`}
                  </span>
                </div>
              )}
              {measurements.lung_symmetry != null && (
                <div className="flex justify-between px-3 py-2 text-xs">
                  <span className="text-slate-500">Symmetry</span>
                  <span className="text-slate-200 font-medium">
                    {typeof measurements.lung_symmetry === 'object'
                      ? (measurements.lung_symmetry.symmetry_ratio != null
                          ? `${(measurements.lung_symmetry.symmetry_ratio * 100).toFixed(1)}% — ${measurements.lung_symmetry.interpretation || ''}`
                          : measurements.lung_symmetry.interpretation || 'N/A')
                      : measurements.lung_symmetry}
                  </span>
                </div>
              )}
              {measurements.lung_symmetry?.left_percent != null && typeof measurements.lung_symmetry === 'object' && (
                <>
                  <div className="flex justify-between px-3 py-2 text-xs">
                    <span className="text-slate-500">Left %</span>
                    <span className="text-slate-200 font-medium">{measurements.lung_symmetry.left_percent}%</span>
                  </div>
                  <div className="flex justify-between px-3 py-2 text-xs">
                    <span className="text-slate-500">Right %</span>
                    <span className="text-slate-200 font-medium">{measurements.lung_symmetry.right_percent}%</span>
                  </div>
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
