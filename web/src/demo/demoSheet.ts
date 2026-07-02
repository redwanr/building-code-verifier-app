/**
 * Synthetic G+9 permit sheet + canned extraction — the publishable demo.
 *
 * Real fixtures are confidential, so demo mode draws its own sheet: an
 * SVG "permit drawing" (site plan, typical floor, ground/parking plan,
 * data tables, title block). The SVG text cells and the param bboxes are
 * generated from the same coordinates, so viewer pins align by construction.
 *
 * Values/confidences port extraction.mock_params() (extraction.py) —
 * mixed confidences so the confirmation gate and all three buckets get
 * exercised without an API call.
 */
import type { ExtractedParam } from '../engine/rules'

export const W = 1684
export const H = 1190

const INK = '#232D3F' // drafting line/text color
const FAINT = '#8C96A8'
const THIN = 'stroke-width="1.2"'

type BBox = [number, number, number, number]
const bboxes: Record<string, BBox> = {}
const parts: string[] = []

function txt(x: number, y: number, s: string, size = 13, opts = ''): string {
  return `<text x="${x}" y="${y}" font-size="${size}" ${opts}>${s}</text>`
}

function labelValue(
  x: number,
  y: number,
  label: string,
  value: string,
  param?: string,
  valueX?: number,
): string {
  const vx = valueX ?? x + 190
  if (param) bboxes[param] = [vx - 6, y - 14, vx + value.length * 8 + 10, y + 6]
  return txt(x, y, label, 12, `fill="${INK}"`) + txt(vx, y, value, 12.5, `fill="${INK}" font-weight="600"`)
}

// ---------------------------------------------------------------- title block
parts.push(`
  <rect x="20" y="20" width="${W - 40}" height="${H - 40}" fill="none" stroke="${INK}" stroke-width="2.5"/>
  <rect x="28" y="28" width="${W - 56}" height="${H - 56}" fill="none" stroke="${INK}" ${THIN}/>
  <g font-family="inherit">
  <rect x="1400" y="40" width="244" height="1110" fill="none" stroke="${INK}" stroke-width="1.6"/>
  ${txt(1522, 90, 'PROPOSED G+9', 19, `text-anchor="middle" font-weight="700" fill="${INK}"`)}
  ${txt(1522, 114, 'RESIDENTIAL BUILDING', 13, `text-anchor="middle" fill="${INK}"`)}
  ${txt(1522, 134, 'OCCUPANCY A-3', 11, `text-anchor="middle" fill="${INK}"`)}
  <line x1="1400" y1="152" x2="1644" y2="152" stroke="${INK}" ${THIN}/>
  ${txt(1522, 176, 'SYNTHETIC DEMO SHEET', 11.5, `text-anchor="middle" font-weight="700" fill="#A6342A"`)}
  ${txt(1522, 192, 'NOT A REAL PROJECT', 10.5, `text-anchor="middle" fill="#A6342A"`)}
  <line x1="1400" y1="206" x2="1644" y2="206" stroke="${INK}" ${THIN}/>
  ${txt(1412, 232, 'SHEET', 10, `fill="${FAINT}"`)}${txt(1412, 250, 'ARCH-01 · COMPOSITE', 12, `fill="${INK}"`)}
  ${txt(1412, 280, 'SCALE', 10, `fill="${FAINT}"`)}${txt(1412, 298, '1:100 / AS SHOWN', 12, `fill="${INK}"`)}
  ${txt(1412, 328, 'DATE', 10, `fill="${FAINT}"`)}${txt(1412, 346, '2026-06', 12, `fill="${INK}"`)}
  </g>`)

// ---------------------------------------------------------------- site plan
{
  const x = 70, y = 90
  const plot = { x: x + 60, y: y + 50, w: 340, h: 360 }
  parts.push(`
  <g>
  ${txt(x, y + 6, 'SITE PLAN', 14, `font-weight="700" fill="${INK}"`)}
  ${txt(x + 84, y + 6, '1:200', 10, `fill="${FAINT}"`)}
  <rect x="${plot.x}" y="${plot.y}" width="${plot.w}" height="${plot.h}" fill="none" stroke="${INK}" stroke-width="1.8"/>
  ${txt(plot.x + plot.w / 2, plot.y - 10, 'PLOT 200.0 m²', 10.5, `text-anchor="middle" fill="${FAINT}"`)}`)
  // footprint: rear gap 20px (1.0m), front gap 30 (1.5m), sides 25 (1.25m)
  const fp = { x: plot.x + 25, y: plot.y + 20, w: plot.w - 50, h: plot.h - 50 }
  parts.push(`
  <rect x="${fp.x}" y="${fp.y}" width="${fp.w}" height="${fp.h}" fill="#EEF1F6" stroke="${INK}" stroke-width="2.2"/>
  ${txt(fp.x + fp.w / 2, fp.y + fp.h / 2, 'BUILDING', 12, `text-anchor="middle" fill="${INK}"`)}
  ${txt(fp.x + fp.w / 2, fp.y + fp.h / 2 + 16, 'FOOTPRINT', 12, `text-anchor="middle" fill="${INK}"`)}`)
  // setback dims
  const dim = (
    x1: number, y1: number, x2: number, y2: number,
    lx: number, ly: number, label: string, param: string,
  ) => {
    bboxes[param] = [lx - 30, ly - 13, lx + 30, ly + 5]
    parts.push(`
  <line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${INK}" ${THIN}/>
  ${txt(lx, ly, label, 11, `text-anchor="middle" fill="${INK}" font-weight="600"`)}`)
  }
  dim(fp.x + fp.w / 2, fp.y + fp.h, fp.x + fp.w / 2, plot.y + plot.h,
    fp.x + fp.w / 2 + 42, fp.y + fp.h + 20, '1.50 m FRONT', 'front_setback_m')
  dim(fp.x + fp.w / 2, plot.y, fp.x + fp.w / 2, fp.y,
    fp.x + fp.w / 2 + 40, fp.y - 6, '1.00 m REAR', 'rear_setback_m')
  dim(plot.x, fp.y + fp.h / 2, fp.x, fp.y + fp.h / 2,
    plot.x - 2, fp.y + fp.h / 2 - 12, '1.25 m SIDE', 'side_setback_m')
  parts.push('</g>')
}

// ---------------------------------------------------------------- typical floor plan
{
  const x = 620, y = 90
  const w = 720, h = 440
  parts.push(`
  <g>
  ${txt(x, y + 6, 'TYPICAL FLOOR PLAN (1st–9th)', 14, `font-weight="700" fill="${INK}"`)}
  ${txt(x + 240, y + 6, '4 UNITS / FLOOR', 10, `fill="${FAINT}"`)}
  <rect x="${x}" y="${y + 24}" width="${w}" height="${h}" fill="none" stroke="${INK}" stroke-width="2.2"/>
  <line x1="${x + w / 2}" y1="${y + 24}" x2="${x + w / 2}" y2="${y + 24 + h}" stroke="${INK}" ${THIN}/>
  <line x1="${x}" y1="${y + 24 + h / 2}" x2="${x + w}" y2="${y + 24 + h / 2}" stroke="${INK}" ${THIN}/>
  ${txt(x + w / 4, y + 24 + h / 4, 'UNIT A', 12, `text-anchor="middle" fill="${FAINT}"`)}
  ${txt(x + (3 * w) / 4, y + 24 + h / 4, 'UNIT B', 12, `text-anchor="middle" fill="${FAINT}"`)}
  ${txt(x + w / 4, y + 24 + (3 * h) / 4, 'UNIT C', 12, `text-anchor="middle" fill="${FAINT}"`)}
  ${txt(x + (3 * w) / 4, y + 24 + (3 * h) / 4, 'UNIT D', 12, `text-anchor="middle" fill="${FAINT}"`)}`)
  // core: one stair + two lifts, centered
  const cx = x + w / 2 - 70, cy = y + 24 + h / 2 - 55
  bboxes['num_exit_stairs'] = [cx, cy, cx + 70, cy + 110]
  bboxes['exit_stair_width_m'] = [cx + 2, cy + 88, cx + 68, cy + 108]
  parts.push(`
  <rect x="${cx}" y="${cy}" width="70" height="110" fill="#fff" stroke="${INK}" stroke-width="2"/>
  ${Array.from({ length: 8 }, (_, i) => `<line x1="${cx + 8}" y1="${cy + 12 + i * 9}" x2="${cx + 62}" y2="${cy + 12 + i * 9}" stroke="${INK}" stroke-width="0.9"/>`).join('')}
  ${txt(cx + 35, cy + 84, 'ST-1', 10.5, `text-anchor="middle" font-weight="700" fill="${INK}"`)}
  ${txt(cx + 35, cy + 102, 'W=1.2 m', 10, `text-anchor="middle" fill="${INK}"`)}`)
  const lx = cx + 82
  bboxes['num_lifts'] = [lx, cy, lx + 58, cy + 110]
  parts.push(`
  <rect x="${lx}" y="${cy}" width="58" height="52" fill="none" stroke="${INK}" stroke-width="1.6"/>
  <line x1="${lx}" y1="${cy}" x2="${lx + 58}" y2="${cy + 52}" stroke="${INK}" stroke-width="0.8"/>
  <line x1="${lx + 58}" y1="${cy}" x2="${lx}" y2="${cy + 52}" stroke="${INK}" stroke-width="0.8"/>
  ${txt(lx + 29, cy + 32, 'L-1', 10, `text-anchor="middle" fill="${INK}"`)}
  <rect x="${lx}" y="${cy + 58}" width="58" height="52" fill="none" stroke="${INK}" stroke-width="1.6"/>
  <line x1="${lx}" y1="${cy + 58}" x2="${lx + 58}" y2="${cy + 110}" stroke="${INK}" stroke-width="0.8"/>
  <line x1="${lx + 58}" y1="${cy + 58}" x2="${lx}" y2="${cy + 110}" stroke="${INK}" stroke-width="0.8"/>
  ${txt(lx + 29, cy + 90, 'L-2', 10, `text-anchor="middle" fill="${INK}"`)}
  </g>`)
}

// ---------------------------------------------------------------- ground floor / parking
{
  const x = 70, y = 640
  parts.push(`
  <g>
  ${txt(x, y, 'GROUND FLOOR PLAN — PARKING', 14, `font-weight="700" fill="${INK}"`)}
  <rect x="${x}" y="${y + 18}" width="690" height="440" fill="none" stroke="${INK}" stroke-width="2.2"/>`)
  const bx = x + 40, by = y + 60, bw = 88, bh = 170
  bboxes['parking_count_on_plan'] = [bx, by, bx + 6 * (bw + 12) - 12, by + bh]
  for (let i = 0; i < 6; i++) {
    const px = bx + i * (bw + 12)
    parts.push(`
  <rect x="${px}" y="${by}" width="${bw}" height="${bh}" fill="none" stroke="${INK}" stroke-width="1.4"/>
  <line x1="${px + 10}" y1="${by + bh - 34}" x2="${px + bw - 10}" y2="${by + 34}" stroke="${FAINT}" stroke-width="1"/>
  ${txt(px + bw / 2, by + bh / 2 + 4, `P${i + 1}`, 12, `text-anchor="middle" font-weight="600" fill="${INK}"`)}`)
  }
  parts.push(`
  ${txt(bx, by + bh + 26, 'CAR PARKING — 6 NOS SHOWN', 11, `fill="${INK}"`)}
  ${txt(bx, by + bh + 46, 'DRIVEWAY 6.0 m', 10, `fill="${FAINT}"`)}
  ${txt(x + 20, y + 400, 'ENTRY', 10, `fill="${FAINT}"`)}
  </g>`)
}

// ---------------------------------------------------------------- data tables
function table(
  x: number,
  y: number,
  w: number,
  title: string,
  rows: Array<[string, string, string?]>,
): number {
  const rh = 26
  parts.push(`
  <g>
  <rect x="${x}" y="${y}" width="${w}" height="${rh}" fill="#E9EDF3" stroke="${INK}" stroke-width="1.4"/>
  ${txt(x + 10, y + 17, title, 11.5, `font-weight="700" fill="${INK}" letter-spacing="1"`)}
  <rect x="${x}" y="${y + rh}" width="${w}" height="${rows.length * rh}" fill="none" stroke="${INK}" stroke-width="1.4"/>`)
  rows.forEach(([label, value, param], i) => {
    const ry = y + rh * (i + 1)
    if (i > 0) parts.push(`<line x1="${x}" y1="${ry}" x2="${x + w}" y2="${ry}" stroke="${FAINT}" stroke-width="0.7"/>`)
    parts.push(labelValue(x + 10, ry + 17, label, value, param, x + w - 130))
  })
  parts.push('</g>')
  return y + rh * (rows.length + 1) + 24
}

{
  const x = 820, w = 520
  let y = 658
  y = table(x, y, w, 'AREA STATEMENT', [
    ['PLOT AREA', '200.0 m²', 'plot_area_m2'],
    ['TOTAL FLOOR AREA', '840.0 m²', 'total_floor_area_m2'],
    ['F.A.R (CLAIMED)', '4.20', 'claimed_far'],
    ['GROUND COVERAGE (MGC)', '58.0 %', 'claimed_mgc_pct'],
    ['STOREYS', 'G+9 (10)', 'num_storeys'],
    ['BUILDING HEIGHT', '35.0 m', 'building_height_m'],
    ['TOTAL UNITS', '36', 'num_units'],
  ])
  y = table(x, y, w, 'PARKING STATEMENT', [
    ['CAR PARKING PROVIDED', '8 NOS', 'parking_provided'],
    ['AS PER TABLE', '8 NOS', 'parking_provided_table'],
  ])
  table(x, y, w, 'FIRE PROVISIONS', [
    ['FIRE ALARM SYSTEM', 'YES', 'has_fire_alarm'],
    ['HYDRANT / STANDPIPE', 'NO', 'has_fire_hydrant_standpipe'],
    ['FIRE-RATED STAIR ENCL.', 'YES', 'has_fire_rated_stair_enclosure'],
    ['FIRE-FIGHTING LIFT', 'NO', 'has_firefighting_lift'],
  ])
}

const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H}" width="${W}" height="${H}"
  font-family="'IBM Plex Mono', ui-monospace, monospace" fill="${INK}">
  <rect width="${W}" height="${H}" fill="#FDFDFB"/>
  ${parts.join('\n')}
</svg>`

export const DEMO_SHEET = {
  width: W,
  height: H,
  svg,
  dataUrl: `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`,
}

// (param, value, unit, confidence) — ported verbatim from extraction._MOCK_ROWS
const MOCK_ROWS: Array<[string, number | boolean, string, number]> = [
  ['building_height_m', 35.0, 'm', 0.80],
  ['num_storeys', 10, '', 0.95],
  ['plot_area_m2', 200.0, 'm²', 0.90],
  ['total_floor_area_m2', 840.0, 'm²', 0.88],
  ['claimed_far', 4.2, '', 0.62], // flagged
  ['claimed_mgc_pct', 58.0, '%', 0.88],
  ['num_exit_stairs', 1, '', 0.55], // flagged
  ['exit_stair_width_m', 1.2, 'm', 0.72],
  ['num_lifts', 2, '', 0.90],
  ['parking_provided', 8, '', 0.90],
  ['parking_provided_table', 8, '', 0.86],
  ['parking_count_on_plan', 6, '', 0.84], // mismatch → red finding
  ['num_units', 36, '', 0.84],
  ['front_setback_m', 1.5, 'm', 0.78],
  ['rear_setback_m', 1.0, 'm', 0.66], // flagged
  ['side_setback_m', 1.25, 'm', 0.74],
  ['has_fire_alarm', true, '', 0.58], // flagged
  ['has_fire_hydrant_standpipe', false, '', 0.80],
  ['has_fire_rated_stair_enclosure', true, '', 0.83],
  ['has_firefighting_lift', false, '', 0.77],
]

export const CONFIDENCE_THRESHOLD = 0.7

export function demoParams(): ExtractedParam[] {
  return MOCK_ROWS.map(([param, value, unit, confidence]) => ({
    param,
    value,
    unit,
    confidence,
    sourcePage: 1,
    sourceCrop: null,
    bbox: bboxes[param] ?? null,
    confirmed: confidence >= CONFIDENCE_THRESHOLD,
  }))
}
