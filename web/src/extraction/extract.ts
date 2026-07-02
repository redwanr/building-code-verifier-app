/**
 * Client-side extraction pipeline — TS port of extraction.py (PRD §8).
 *
 * pdf.js rasterizes in the browser (the drawing only leaves the machine as
 * page PNGs sent to the worker proxy, which attaches the provider key).
 * Same prompt and post-processing semantics as the Python engine: vision
 * bboxes validated, confidence < 0.7 → unconfirmed (FR-4), best read wins
 * when a param appears on multiple pages.
 */
import type { ExtractedParam } from '../engine/rules'

export const CONFIDENCE_THRESHOLD = 0.7
const DPI = 200
const CROP_PAD = 40
const MAX_PAGES = 2

export const CLAUDE_MODEL = 'claude-opus-4-8'
export const GEMINI_MODEL = 'gemini-3.5-flash'

export const PARAM_NAMES = [
  'building_height_m', 'num_storeys', 'plot_area_m2', 'total_floor_area_m2',
  'claimed_far', 'claimed_mgc_pct',
  'num_exit_stairs', 'exit_stair_width_m', 'num_lifts',
  'parking_provided', 'parking_provided_table', 'parking_count_on_plan',
  'num_units',
  'front_setback_m', 'rear_setback_m', 'side_setback_m',
  'has_fire_alarm', 'has_fire_hydrant_standpipe',
  'has_fire_rated_stair_enclosure', 'has_firefighting_lift',
]

export const EXTRACTION_PROMPT = `You are reading one page of a RAJUK building-approval permit sheet \
(Dhaka, Bangladesh): a dense raster drawing with floor plans, elevations, sections, \
and data tables (area/FAR/MGC/setback/parking). Labels are mostly English; some \
Bangla may appear in tables.

Extract ONLY values you can actually see printed as text/table values or count \
directly (e.g. number of stair cores, lifts, parking spots drawn). NEVER guess or \
infer a value that is not on the page. Target parameters:
${JSON.stringify(PARAM_NAMES, null, 2)}

Return JSON exactly in this shape:
{"params": [{
  "param": "<name from the list>",
  "value": <number or boolean>,
  "unit": "<m | m2 | ratio | percent | count | bool>",
  "confidence": <0.0-1.0, your honest confidence in this exact reading>,
  "bbox": [x0, y0, x1, y1] or null,   // pixel coords on THIS image; null if unsure
  "location_note": "<where on the sheet this value appears>"
}]}

Rules:
- Omit any parameter not visible on this page. An omitted param is better than a guess.
- has_* params: true only if the provision is explicitly shown/noted; omit otherwise.
- parking_provided_table = the number stated in the parking table; \
parking_count_on_plan = spots you can count drawn on the plan. Report both if visible.
- Convert feet to metres where units are imperial; note the conversion in location_note.
- Be conservative with confidence: dense/blurry/ambiguous reads get < 0.7.`

const RESPONSE_SCHEMA = {
  type: 'object',
  properties: {
    params: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          param: { type: 'string', enum: PARAM_NAMES },
          value: { anyOf: [{ type: 'number' }, { type: 'boolean' }] },
          unit: { type: 'string' },
          confidence: { type: 'number' },
          bbox: { anyOf: [{ type: 'array', items: { type: 'number' } }, { type: 'null' }] },
          location_note: { type: 'string' },
        },
        required: ['param', 'value', 'unit', 'confidence', 'bbox', 'location_note'],
        additionalProperties: false,
      },
    },
  },
  required: ['params'],
  additionalProperties: false,
}

// ---------------------------------------------------------------- parse (pure)

interface ResponseRow {
  param: string
  value: number | boolean
  unit?: string
  confidence?: number
  bbox?: unknown
  location_note?: string
}

export function validBbox(bbox: unknown, pageW: number, pageH: number): [number, number, number, number] | null {
  if (!Array.isArray(bbox) || bbox.length !== 4) return null
  const [x0, y0, x1, y1] = bbox.map(Number)
  if ([x0, y0, x1, y1].some(Number.isNaN)) return null
  if (!(x0 >= 0 && x0 < x1 && x1 <= pageW && y0 >= 0 && y0 < y1 && y1 <= pageH)) return null
  return [x0, y0, x1, y1]
}

export function paramsFromResponse(
  response: { params?: ResponseRow[] },
  sourcePage: number,
  pageW: number,
  pageH: number,
): ExtractedParam[] {
  return (response.params ?? []).map((row) => {
    const confidence = Number(row.confidence ?? 0)
    const bbox = validBbox(row.bbox, pageW, pageH)
    return {
      param: row.param,
      value: row.value,
      unit: row.unit ?? '',
      confidence,
      sourcePage,
      sourceCrop: null, // cut in the browser after parse (needs the canvas)
      cropFallbackNote: bbox ? null : row.location_note ?? null,
      bbox,
      confirmed: confidence >= CONFIDENCE_THRESHOLD,
    }
  })
}

export function bestPerParam(params: ExtractedParam[]): ExtractedParam[] {
  const best = new Map<string, ExtractedParam>()
  for (const p of params) {
    const cur = best.get(p.param)
    if (!cur || p.confidence > cur.confidence) best.set(p.param, p)
  }
  return [...best.values()]
}

// ---------------------------------------------------------------- browser-only

export interface RenderedPage {
  canvas: HTMLCanvasElement
  dataUrl: string
  width: number
  height: number
}

export async function rasterizePdf(file: File): Promise<RenderedPage[]> {
  const pdfjs = await import('pdfjs-dist')
  pdfjs.GlobalWorkerOptions.workerSrc = new URL(
    'pdfjs-dist/build/pdf.worker.min.mjs',
    import.meta.url,
  ).toString()

  const doc = await pdfjs.getDocument({ data: await file.arrayBuffer() }).promise
  const pages: RenderedPage[] = []
  for (let i = 1; i <= Math.min(doc.numPages, MAX_PAGES); i++) {
    const page = await doc.getPage(i)
    const viewport = page.getViewport({ scale: DPI / 72 })
    const canvas = document.createElement('canvas')
    canvas.width = Math.floor(viewport.width)
    canvas.height = Math.floor(viewport.height)
    await page.render({ canvas, canvasContext: canvas.getContext('2d')!, viewport }).promise
    pages.push({
      canvas,
      dataUrl: canvas.toDataURL('image/png'),
      width: canvas.width,
      height: canvas.height,
    })
  }
  return pages
}

/** Padded evidence crop for the audit trail — client-side, mirrors render_crop. */
export function cutCrop(page: RenderedPage, bbox: [number, number, number, number]): string {
  const [x0, y0, x1, y1] = bbox
  const cx = Math.max(0, x0 - CROP_PAD)
  const cy = Math.max(0, y0 - CROP_PAD)
  const cw = Math.min(page.width, x1 + CROP_PAD) - cx
  const ch = Math.min(page.height, y1 + CROP_PAD) - cy
  const out = document.createElement('canvas')
  out.width = cw
  out.height = ch
  out.getContext('2d')!.drawImage(page.canvas, cx, cy, cw, ch, 0, 0, cw, ch)
  return out.toDataURL('image/png')
}

// ---------------------------------------------------------------- worker calls

export const WORKER_URL: string = import.meta.env.VITE_WORKER_URL ?? ''

export class AuthError extends Error {}

async function callWorker(
  provider: 'gemini' | 'claude',
  pngBase64: string,
  password: string,
): Promise<{ params?: ResponseRow[] }> {
  const body =
    provider === 'gemini'
      ? {
          contents: [{
            parts: [
              { inline_data: { mime_type: 'image/png', data: pngBase64 } },
              { text: EXTRACTION_PROMPT },
            ],
          }],
          generationConfig: { response_mime_type: 'application/json' },
        }
      : {
          max_tokens: 16000,
          output_config: { format: { type: 'json_schema', schema: RESPONSE_SCHEMA } },
          messages: [{
            role: 'user',
            content: [
              { type: 'image', source: { type: 'base64', media_type: 'image/png', data: pngBase64 } },
              { type: 'text', text: EXTRACTION_PROMPT },
            ],
          }],
        }

  const res = await fetch(`${WORKER_URL}/extract`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${password}` },
    body: JSON.stringify({
      provider,
      model: provider === 'gemini' ? GEMINI_MODEL : CLAUDE_MODEL,
      body,
    }),
  })
  if (res.status === 401) throw new AuthError('Wrong password.')
  if (!res.ok) throw new Error(`Extraction call failed (${res.status}): ${await res.text()}`)

  const data = await res.json()
  const text: string =
    provider === 'gemini'
      ? data.candidates?.[0]?.content?.parts?.map((p: { text?: string }) => p.text ?? '').join('') ?? ''
      : data.content?.find((b: { type: string }) => b.type === 'text')?.text ?? ''
  return JSON.parse(text)
}

export async function verifyPassword(password: string): Promise<boolean> {
  const res = await fetch(`${WORKER_URL}/auth`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${password}` },
  })
  return res.ok
}

// ---------------------------------------------------------------- pipeline

export async function extract(
  file: File,
  provider: 'gemini' | 'claude',
  password: string,
  onProgress: (msg: string) => void,
): Promise<{ pages: RenderedPage[]; params: ExtractedParam[] }> {
  onProgress('Rendering the sheet in your browser…')
  const pages = await rasterizePdf(file)

  const all: ExtractedParam[] = []
  for (const [i, page] of pages.entries()) {
    onProgress(`Reading page ${i + 1} of ${pages.length} with ${provider}…`)
    const base64 = page.dataUrl.split(',')[1]
    const response = await callWorker(provider, base64, password)
    const parsed = paramsFromResponse(response, i + 1, page.width, page.height)
    for (const p of parsed) if (p.bbox) p.sourceCrop = cutCrop(page, p.bbox)
    all.push(...parsed)
  }
  return { pages, params: bestPerParam(all) }
}
