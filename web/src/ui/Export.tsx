import { useState } from 'react'

import { newReport, renderHtml, renderMarkdown } from '../engine/report'
import { useStore } from '../store'
import { usePanelData } from './Panel'

function download(name: string, content: string, mime: string) {
  const a = document.createElement('a')
  a.href = URL.createObjectURL(new Blob([content], { type: mime }))
  a.download = name
  a.click()
  URL.revokeObjectURL(a.href)
}

export function Export() {
  const [open, setOpen] = useState(false)
  const [fmt, setFmt] = useState<'html' | 'md'>('html')
  const [includeCrops, setIncludeCrops] = useState(false)
  const packNames = useStore((s) => s.packNames)
  const { params, supplied, findings } = usePanelData()

  const doExport = () => {
    const allParams = [
      ...params,
      ...Object.entries(supplied).map(([name, value]) => ({
        param: name, value, unit: '', confidence: 1.0,
        sourcePage: 0, sourceCrop: null, confirmed: true,
      })),
    ]
    const exportFindings = includeCrops
      ? findings
      : findings.map((f) => ({ ...f, sheetLocation: null }))
    const report = newReport(packNames, allParams, exportFindings)
    if (fmt === 'md') {
      download(`findings_${report.submissionId.slice(0, 8)}.md`, renderMarkdown(report), 'text/markdown')
    } else {
      download(`findings_${report.submissionId.slice(0, 8)}.html`, renderHtml(report), 'text/html')
    }
    setOpen(false)
  }

  return (
    <div className="export-wrap">
      <button className="btn primary" onClick={() => setOpen(!open)} aria-expanded={open}>
        Export report
      </button>
      {open && (
        <div className="export-pop">
          <div className="k">Format</div>
          <label><input type="radio" checked={fmt === 'html'} onChange={() => setFmt('html')} /> HTML (print → PDF)</label>
          <label><input type="radio" checked={fmt === 'md'} onChange={() => setFmt('md')} /> Markdown</label>
          <div className="k">Includes</div>
          <div className="fixed">risk summary · findings + reviewer notes · parameter audit trail · disclaimer + rule-pack versions</div>
          <label>
            <input type="checkbox" checked={includeCrops} onChange={(e) => setIncludeCrops(e.target.checked)} />
            evidence crops <span className="warn">confidential</span>
          </label>
          <button className="btn primary" onClick={doExport}>Download</button>
        </div>
      )}
    </div>
  )
}
