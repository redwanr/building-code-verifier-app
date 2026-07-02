import { DEMO_SHEET, demoParams } from '../demo/demoSheet'
import { useStore } from '../store'

export function Upload() {
  const openReview = useStore((s) => s.openReview)

  const openDemo = () =>
    openReview('synthetic-demo-g9.svg', {
      dataUrl: DEMO_SHEET.dataUrl,
      width: DEMO_SHEET.width,
      height: DEMO_SHEET.height,
    }, demoParams())

  return (
    <div className="upload-stage">
      <div className="upload-title">
        <h1>Put the sheet on the table</h1>
        <p>
          Drop a RAJUK permit sheet (raster PDF). The extractor reads the data
          tables, pins every value it finds on the drawing, and runs the code
          checks as you confirm each read.
        </p>
      </div>
      <div className="dropzone">
        <span>PDF · ≤ 2 pages · rendered in your browser</span>
        <span style={{ color: 'var(--text-faint)' }}>live extraction arrives in the next build</span>
        <div className="corner">
          RAJUK VERIFIER<br />DECISION SUPPORT — NOT CERTIFICATION
        </div>
      </div>
      <div className="demo-line">
        No sheet at hand? <button onClick={openDemo}>Open the demo review</button> — a synthetic
        G+9 sheet, no upload, no API credits.
      </div>
    </div>
  )
}
