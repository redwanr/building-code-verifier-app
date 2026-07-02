import { useRef, useState } from 'react'

import { DEMO_SHEET, demoParams } from '../demo/demoSheet'
import { AuthError, extract, rasterizePdf, WORKER_URL } from '../extraction/extract'
import { loadDraft, useStore } from '../store'

const PW_KEY = 'rajuk-verifier-pw'

async function fileKeyOf(file: File): Promise<string> {
  const digest = await crypto.subtle.digest('SHA-256', await file.arrayBuffer())
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, '0')).join('')
}

export function Upload() {
  const openReview = useStore((s) => s.openReview)
  const [provider, setProvider] = useState<'gemini' | 'claude'>('gemini')
  const [password, setPassword] = useState(() => localStorage.getItem(PW_KEY) ?? '')
  const [busy, setBusy] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [dragOver, setDragOver] = useState(false)
  const fileInput = useRef<HTMLInputElement>(null)

  const canExtract = Boolean(WORKER_URL)
  const draft = loadDraft()

  const openDemo = () => {
    const restore = draft?.fileKey === 'demo' ? draft : undefined
    openReview('synthetic-demo-g9.svg', [{
      dataUrl: DEMO_SHEET.dataUrl,
      width: DEMO_SHEET.width,
      height: DEMO_SHEET.height,
    }], restore?.params ?? demoParams(), 'demo', restore)
  }

  const run = async (file: File) => {
    setError(null)
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setError('That is not a PDF. Drop the permit sheet as a raster PDF.')
      return
    }
    setBusy('Starting…')
    try {
      const fileKey = await fileKeyOf(file)

      // same file as the saved draft → re-render locally, restore the review,
      // skip the extraction call entirely
      if (draft && draft.fileKey === fileKey) {
        setBusy('Resuming your review — re-rendering the sheet locally…')
        const pages = await rasterizePdf(file)
        openReview(
          file.name,
          pages.map((p) => ({ dataUrl: p.dataUrl, width: p.width, height: p.height })),
          draft.params, fileKey, draft,
        )
        return
      }

      if (!password) {
        setError('Enter the reviewer password first — extraction is gated.')
        return
      }
      localStorage.setItem(PW_KEY, password)
      const { pages, params } = await extract(file, provider, password, setBusy)
      if (params.length === 0) {
        setError('The extractor found no readable parameters on this sheet. Try the other provider, or check the PDF renders legibly.')
        return
      }
      openReview(
        file.name,
        pages.map((p) => ({ dataUrl: p.dataUrl, width: p.width, height: p.height })),
        params, fileKey,
      )
    } catch (e) {
      if (e instanceof AuthError) {
        localStorage.removeItem(PW_KEY)
        setError('Wrong password — extraction refused.')
      } else {
        setError(`Extraction failed: ${e instanceof Error ? e.message : String(e)}`)
      }
    } finally {
      setBusy(null)
    }
  }

  return (
    <div className="upload-stage">
      <div className="upload-title">
        <h1>Put the sheet on the table</h1>
        <p>
          Drop a RAJUK permit sheet (raster PDF). It renders in your browser;
          page images go only to the extraction model on a no-training API tier.
          Checks run as you confirm each read.
        </p>
      </div>

      <div
        className={`dropzone${dragOver ? ' active' : ''}`}
        role="button"
        tabIndex={0}
        onClick={() => canExtract && !busy && fileInput.current?.click()}
        onKeyDown={(e) => e.key === 'Enter' && canExtract && fileInput.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault()
          setDragOver(false)
          const f = e.dataTransfer.files?.[0]
          if (f && canExtract && !busy) run(f)
        }}
      >
        <input
          ref={fileInput}
          type="file"
          accept="application/pdf"
          hidden
          onChange={(e) => e.target.files?.[0] && run(e.target.files[0])}
        />
        {busy ? (
          <span style={{ color: 'var(--clay)' }}>{busy}</span>
        ) : (
          <>
            <span>PDF · ≤ 2 pages · rendered in your browser</span>
            <span style={{ color: 'var(--text-faint)' }}>
              {canExtract ? 'drop the sheet here, or click to browse' : 'extraction proxy not configured — demo only'}
            </span>
          </>
        )}
        <div className="corner">
          RAJUK VERIFIER<br />DECISION SUPPORT — NOT CERTIFICATION
        </div>
      </div>

      {canExtract && (
        <div className="extract-config">
          <label>
            <span>reviewer password</span>
            <input
              type="password"
              value={password}
              autoComplete="current-password"
              onChange={(e) => setPassword(e.target.value)}
            />
          </label>
          <label>
            <span>extraction model</span>
            <select value={provider} onChange={(e) => setProvider(e.target.value as 'gemini' | 'claude')}>
              <option value="gemini">Gemini</option>
              <option value="claude">Claude</option>
            </select>
          </label>
        </div>
      )}

      {error && <div className="upload-error">{error}</div>}

      {draft && (
        <div className="resume-line">
          Unfinished review of <b>{draft.sheetName}</b> saved{' '}
          {new Date(draft.savedAt).toLocaleString()}.{' '}
          {draft.fileKey === 'demo'
            ? 'Open the demo review below to pick it up.'
            : 'Re-drop the same PDF to resume it — no re-extraction, no credits.'}
        </div>
      )}

      <div className="demo-line">
        No sheet at hand? <button onClick={openDemo}>Open the demo review</button> — a synthetic
        G+9 sheet, no upload, no API credits.
      </div>
    </div>
  )
}
