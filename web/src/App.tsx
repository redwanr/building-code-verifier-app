import { useEffect, useState } from 'react'

import { fetchPacks } from './engine/packs'
import { useStore } from './store'
import { Panel } from './ui/Panel'
import { Upload } from './ui/Upload'
import { Viewer } from './ui/Viewer'

const DISCLAIMER_FULL =
  'This tool gives a first-pass, automated triage of possible code issues for review by a ' +
  'qualified, licensed architect/engineer. It does not approve, certify, or guarantee compliance ' +
  'with RAJUK rules or BNBC. Extracted values and findings may be wrong. A qualified professional ' +
  'must independently verify everything. No legal reliance.'

export default function App() {
  const stage = useStore((s) => s.stage)
  const packNames = useStore((s) => s.packNames)
  const setPacks = useStore((s) => s.setPacks)
  const sheetName = useStore((s) => s.sheetName)
  const reset = useStore((s) => s.reset)
  const [fullNotice, setFullNotice] = useState(false)

  useEffect(() => {
    fetchPacks().then(({ rules, packNames }) => setPacks(rules, packNames))
      .catch((e) => console.error('rule packs failed to load', e))
  }, [setPacks])

  return (
    <div className="app">
      <header className="topbar">
        <div className="mark" aria-hidden />
        <div className="brand">
          <b>RAJUK Verifier</b>
          <span>permit-sheet triage · decision support</span>
        </div>
        <div className="pack-chips">
          {packNames.map((p) => (
            <span key={p} className="pack-chip"><i />{p}</span>
          ))}
        </div>
        <div className="spacer" />
        {stage === 'workspace' && (
          <>
            <span className="sheet-name">{sheetName}</span>
            <button className="btn quiet" onClick={reset}>New review</button>
            <button className="btn primary" disabled title="Export lands in the next build">
              Export report
            </button>
          </>
        )}
      </header>

      <div className="disclaimer">
        <b>Decision-support only — not a certification.</b>
        <span>A licensed professional must verify every value.</span>
        <button className="btn quiet" style={{ padding: '1px 8px', fontSize: 11 }} onClick={() => setFullNotice(!fullNotice)}>
          {fullNotice ? 'hide notice' : 'full notice'}
        </button>
        {fullNotice && <span className="full">{DISCLAIMER_FULL}</span>}
      </div>

      {stage === 'upload' ? (
        <Upload />
      ) : (
        <main className="workspace">
          <Viewer />
          <Panel />
        </main>
      )}
    </div>
  )
}
