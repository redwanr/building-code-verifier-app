/**
 * Sheet viewer — the drafting table. Wheel zooms around the cursor, drag
 * pans, pins are crosshair survey markers at each extracted value's bbox.
 * Pins keep constant screen size via inverse scale.
 */
import { useCallback, useEffect, useRef, useState } from 'react'

import { CONFIDENCE_THRESHOLD, useStore } from '../store'

interface View {
  scale: number
  tx: number
  ty: number
}

export function Viewer() {
  const sheet = useStore((s) => s.sheet)
  const params = useStore((s) => s.params)
  const focusParam = useStore((s) => s.focusParam)
  const setFocusParam = useStore((s) => s.setFocusParam)

  const host = useRef<HTMLDivElement>(null)
  const [view, setView] = useState<View>({ scale: 0.4, tx: 0, ty: 0 })
  const [panning, setPanning] = useState(false)
  const drag = useRef<{ x: number; y: number; tx: number; ty: number; moved: boolean } | null>(null)

  const fit = useCallback(() => {
    if (!host.current || !sheet) return
    const { clientWidth: w, clientHeight: h } = host.current
    const scale = Math.min((w - 70) / sheet.width, (h - 70) / sheet.height)
    setView({ scale, tx: (w - sheet.width * scale) / 2, ty: (h - sheet.height * scale) / 2 })
  }, [sheet])

  useEffect(() => {
    fit()
    const onResize = () => fit()
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [fit])

  // panel focus → glide the pin to center
  useEffect(() => {
    if (!focusParam || !host.current || !sheet) return
    const p = params.find((q) => q.param === focusParam)
    if (!p?.bbox) return
    const [x0, y0, x1, y1] = p.bbox
    const cx = (x0 + x1) / 2
    const cy = (y0 + y1) / 2
    setView((v) => ({
      ...v,
      tx: host.current!.clientWidth / 2 - cx * v.scale,
      ty: host.current!.clientHeight / 2 - cy * v.scale,
    }))
  }, [focusParam, params, sheet])

  const zoomAt = (clientX: number, clientY: number, factor: number) => {
    const rect = host.current!.getBoundingClientRect()
    const px = clientX - rect.left
    const py = clientY - rect.top
    setView((v) => {
      const scale = Math.min(4, Math.max(0.05, v.scale * factor))
      const k = scale / v.scale
      return { scale, tx: px - (px - v.tx) * k, ty: py - (py - v.ty) * k }
    })
  }

  if (!sheet) return null

  return (
    <div
      ref={host}
      className={`viewer${panning ? ' panning' : ''}`}
      onWheel={(e) => zoomAt(e.clientX, e.clientY, e.deltaY < 0 ? 1.12 : 1 / 1.12)}
      onPointerDown={(e) => {
        drag.current = { x: e.clientX, y: e.clientY, tx: view.tx, ty: view.ty, moved: false }
        setPanning(true)
        ;(e.target as Element).setPointerCapture?.(e.pointerId)
      }}
      onPointerMove={(e) => {
        if (!drag.current) return
        const dx = e.clientX - drag.current.x
        const dy = e.clientY - drag.current.y
        if (Math.abs(dx) + Math.abs(dy) > 3) drag.current.moved = true
        setView((v) => ({ ...v, tx: drag.current!.tx + dx, ty: drag.current!.ty + dy }))
      }}
      onPointerUp={() => {
        drag.current = null
        setPanning(false)
      }}
    >
      <div
        className="viewer-canvas"
        style={{ transform: `translate(${view.tx}px, ${view.ty}px) scale(${view.scale})` }}
      >
        <img src={sheet.dataUrl} width={sheet.width} height={sheet.height} alt="Permit sheet" />
        {params.map((p) => {
          if (!p.bbox) return null
          const [x0, y0, , y1] = p.bbox
          const flagged = p.confidence < CONFIDENCE_THRESHOLD && !p.confirmed
          const cls = focusParam === p.param ? 'focused' : flagged ? 'flagged' : p.confirmed ? 'confirmed' : ''
          return (
            <div
              key={p.param}
              className={`pin ${cls}`}
              style={{
                left: x0 - 17,
                top: (y0 + y1) / 2,
                transform: `scale(${1 / view.scale})`,
              }}
            >
              <button
                aria-label={`${p.param} = ${String(p.value)}`}
                onClick={(e) => {
                  e.stopPropagation()
                  if (drag.current?.moved) return
                  setFocusParam(p.param)
                }}
              />
              {focusParam === p.param && (
                <span className="callout">
                  {p.param} <small>= {String(p.value)}{p.unit ? ` ${p.unit}` : ''}</small>
                </span>
              )}
            </div>
          )
        })}
      </div>
      <div className="zoombar">
        <button aria-label="Zoom out" onClick={(e) => { e.stopPropagation(); zoomAt(host.current!.clientWidth / 2, host.current!.clientHeight / 2, 1 / 1.25) }}>−</button>
        <span className="pct">{Math.round(view.scale * 100)}%</span>
        <button aria-label="Zoom in" onClick={(e) => { e.stopPropagation(); zoomAt(host.current!.clientWidth / 2, host.current!.clientHeight / 2, 1.25) }}>+</button>
        <button onClick={(e) => { e.stopPropagation(); fit() }}>fit</button>
      </div>
    </div>
  )
}
