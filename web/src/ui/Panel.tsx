/**
 * Review panel — VALUES (confirm the extraction, supply the limits the sheet
 * can't know) and CHECKS (live verdicts). Verdicts recompute on every edit;
 * unconfirmed/missing inputs keep their rules at "cannot evaluate" (FR-9).
 */
import { useMemo, useState } from 'react'

import type { ExtractedParam, Finding } from '../engine/rules'
import { CONFIDENCE_THRESHOLD, liveFindings, missingInputs, useStore } from '../store'

const BUCKETS = [
  { key: 'likely_violation', label: 'Likely violation', cls: 'viol', color: 'var(--viol)' },
  { key: 'needs_verification', label: 'Needs verification', cls: 'verify', color: 'var(--verify)' },
  { key: 'appears_compliant', label: 'Appears compliant', cls: 'ok', color: 'var(--ok)' },
] as const

const SEV_ORDER: Record<string, number> = { critical: 0, high: 1, medium: 2, moderate: 2, low: 3 }

function confColor(c: number): string {
  return c >= 0.8 ? 'var(--ok)' : c >= 0.5 ? 'var(--verify)' : 'var(--viol)'
}

export function usePanelData() {
  const rules = useStore((s) => s.rules)
  const params = useStore((s) => s.params)
  const supplied = useStore((s) => s.supplied)
  const reviewerActions = useStore((s) => s.reviewerActions)
  const findings = useMemo(
    () => liveFindings(rules, params, supplied, reviewerActions),
    [rules, params, supplied, reviewerActions],
  )
  const missing = useMemo(() => missingInputs(rules, params, supplied), [rules, params, supplied])
  return { rules, params, supplied, findings, missing }
}

export function Panel() {
  const tab = useStore((s) => s.tab)
  const setTab = useStore((s) => s.setTab)
  const { params, findings } = usePanelData()

  const counts = Object.fromEntries(
    BUCKETS.map((b) => [b.key, findings.filter((f) => f.bucket === b.key).length]),
  )
  const toConfirm = params.filter((p) => !p.confirmed).length

  return (
    <aside className="panel">
      <div className="verdict-strip">
        <div className="verdict-tile viol"><div className="n">{counts.likely_violation}</div><div className="lbl">Likely violation</div></div>
        <div className="verdict-tile verify"><div className="n">{counts.needs_verification}</div><div className="lbl">Needs verification</div></div>
        <div className="verdict-tile ok"><div className="n">{counts.appears_compliant}</div><div className="lbl">Appears compliant</div></div>
      </div>
      <div className="tabs" role="tablist">
        <button role="tab" aria-selected={tab === 'values'} className={tab === 'values' ? 'on' : ''} onClick={() => setTab('values')}>
          VALUES{toConfirm > 0 && <span className="badge warn">{toConfirm} to confirm</span>}
        </button>
        <button role="tab" aria-selected={tab === 'checks'} className={tab === 'checks' ? 'on' : ''} onClick={() => setTab('checks')}>
          CHECKS<span className="badge">{findings.length}</span>
        </button>
      </div>
      <div className="panel-scroll">{tab === 'values' ? <ValuesTab /> : <ChecksTab />}</div>
    </aside>
  )
}

// ---------------------------------------------------------------- values
function ValueRow({ p, feeds }: { p: ExtractedParam; feeds: string[] }) {
  const focusParam = useStore((s) => s.focusParam)
  const setFocusParam = useStore((s) => s.setFocusParam)
  const setParamValue = useStore((s) => s.setParamValue)
  const setConfirmed = useStore((s) => s.setConfirmed)

  const flagged = p.confidence < CONFIDENCE_THRESHOLD
  const cls = `vrow${focusParam === p.param ? ' focused' : ''}${flagged && !p.confirmed ? ' flagged' : ''}`

  return (
    <div
      className={cls}
      id={`vrow-${p.param}`}
      onClick={() => setFocusParam(p.param)}
    >
      <div className="name">
        {p.param}
        {p.unit && <small>{p.unit}</small>}
        {flagged && !p.confirmed && <span className="review-tag">NEEDS REVIEW</span>}
      </div>
      <div className="conf">
        <span className="track"><i style={{ width: `${p.confidence * 100}%`, background: confColor(p.confidence) }} /></span>
        <span className="val">{p.confidence.toFixed(2)}</span>
      </div>
      <div className="controls" onClick={(e) => e.stopPropagation()}>
        {typeof p.value === 'boolean' ? (
          <span className="bool">
            <button className={p.value ? 'on' : ''} onClick={() => setParamValue(p.param, true)}>present</button>
            <button className={!p.value ? 'on' : ''} onClick={() => setParamValue(p.param, false)}>absent</button>
          </span>
        ) : (
          <input
            type="number"
            value={Number(p.value)}
            onChange={(e) => setParamValue(p.param, e.target.valueAsNumber)}
          />
        )}
        {p.confirmed ? (
          <button className="confirm-btn done" disabled>✓ confirmed</button>
        ) : (
          <button className={`confirm-btn${flagged ? ' needed' : ''}`} onClick={() => setConfirmed(p.param, true)}>
            Confirm
          </button>
        )}
      </div>
      {p.editedFrom !== undefined && p.editedFrom !== null && p.editedFrom !== p.value && (
        <div className="edited">edited — extractor read {String(p.editedFrom)}</div>
      )}
      {feeds.length > 0 && <div className="feeds">feeds {feeds.join(' · ')}</div>}
    </div>
  )
}

function ValuesTab() {
  const { rules, params, supplied, missing } = usePanelData()
  const setSupplied = useStore((s) => s.setSupplied)

  const feedsMap = useMemo(() => {
    const m: Record<string, string[]> = {}
    for (const r of rules) for (const p of r.parameters) (m[p] ??= []).push(r.id)
    return m
  }, [rules])

  const flagged = params.filter((p) => !p.confirmed)
  const rest = params.filter((p) => p.confirmed)

  return (
    <>
      <div className="section-note">
        Checks only use values you confirm. Low-confidence reads wait for you — nothing passes on a guess.
      </div>
      {flagged.length > 0 && <div className="section-head">To confirm ({flagged.length})</div>}
      {flagged.map((p) => <ValueRow key={p.param} p={p} feeds={feedsMap[p.param] ?? []} />)}
      {rest.length > 0 && <div className="section-head">Confirmed reads</div>}
      {rest.map((p) => <ValueRow key={p.param} p={p} feeds={feedsMap[p.param] ?? []} />)}

      <div className="section-head">You supply ({missing.length})</div>
      <div className="supply-note">
        Ward/LUC-specific limits the sheet can't state. Leave blank and the rule reports “cannot evaluate”.
      </div>
      {missing.map((name) => (
        <div className="vrow" key={name}>
          <div className="name">{name}</div>
          <div />
          <div className="controls">
            <input
              type="number"
              placeholder="—"
              value={supplied[name] ?? ''}
              onChange={(e) => setSupplied(name, e.target.value === '' ? null : e.target.valueAsNumber)}
            />
          </div>
          <div className="feeds">feeds {(feedsMap[name] ?? []).join(' · ')}</div>
        </div>
      ))}
    </>
  )
}

// ---------------------------------------------------------------- checks
function CheckCard({ f }: { f: Finding }) {
  const [open, setOpen] = useState(false)
  const setFocusParam = useStore((s) => s.setFocusParam)
  const setTab = useStore((s) => s.setTab)
  const setReviewerAction = useStore((s) => s.setReviewerAction)
  const params = useStore((s) => s.params)

  const cls = BUCKETS.find((b) => b.key === f.bucket)!.cls
  const blocked = f.reason.startsWith('Cannot evaluate')
  const missingNames = blocked
    ? f.reason.replace(/^Cannot evaluate — input missing or unconfirmed: /, '').replace(/\.$/, '').split(', ')
    : []

  const jump = (name: string) => {
    setTab('values')
    setFocusParam(params.some((p) => p.param === name) ? name : null)
    document.getElementById(`vrow-${name}`)?.scrollIntoView({ block: 'center' })
  }

  return (
    <div className={`check ${cls}`}>
      <button className="check-head" onClick={() => setOpen(!open)} aria-expanded={open}>
        <span className={`sev ${f.severity.toLowerCase()}`}>{f.severity}</span>
        <span className="rule-id">{f.ruleId}</span>
        <span className={`regime ${f.regime}`}>{f.regime}</span>
      </button>
      {blocked ? (
        <div className="check-blocked">
          Cannot evaluate — needs{' '}
          {missingNames.map((n, i) => (
            <span key={n}>
              {i > 0 && ', '}
              <button onClick={() => jump(n)}>{n}</button>
            </span>
          ))}
        </div>
      ) : (
        <div className="check-reason">
          {f.reason.split('[VERIFY]').map((part, i) => (
            <span key={i}>
              {i > 0 && <span className="verify-mark">[VERIFY]</span>}
              {part}
            </span>
          ))}
        </div>
      )}
      {!blocked && Object.keys(f.inputsUsed).length > 0 && (
        <div className="check-inputs">
          {Object.entries(f.inputsUsed).map(([k, v]) => (
            <button key={k} onClick={() => jump(k)}>
              {k}: {String(v)}
            </button>
          ))}
        </div>
      )}
      {open && (
        <div className="check-body">
          <div className="check-cite">{f.citation}</div>
          <div className="check-fix">
            <b>{f.bucket === 'appears_compliant' ? 'Note' : 'Suggested fix'}</b>
            {f.remediation}
          </div>
          <div className="check-actions">
            <button
              className={`act${f.userAction === 'accept' ? ' on-accept' : ''}`}
              onClick={() => setReviewerAction(f.ruleId, { action: f.userAction === 'accept' ? undefined : 'accept' })}
            >
              Accept
            </button>
            <button
              className={`act${f.userAction === 'dismiss' ? ' on-dismiss' : ''}`}
              onClick={() => setReviewerAction(f.ruleId, { action: f.userAction === 'dismiss' ? undefined : 'dismiss' })}
            >
              Dismiss
            </button>
            <input
              className="note"
              placeholder="Note for the report…"
              value={f.userNote ?? ''}
              onChange={(e) => setReviewerAction(f.ruleId, { note: e.target.value })}
            />
          </div>
        </div>
      )}
    </div>
  )
}

function ChecksTab() {
  const { findings } = usePanelData()
  return (
    <>
      {BUCKETS.map((b) => {
        const group = findings
          .filter((f) => f.bucket === b.key)
          .sort((x, y) => (SEV_ORDER[x.severity.toLowerCase()] ?? 9) - (SEV_ORDER[y.severity.toLowerCase()] ?? 9))
        if (!group.length) return null
        return (
          <div key={b.key}>
            <div className="check-group-head">
              <i style={{ background: b.color }} />
              {b.label}
              <span className="count">{group.length}</span>
            </div>
            {group.map((f) => <CheckCard key={f.ruleId} f={f} />)}
          </div>
        )
      })}
    </>
  )
}
