import { create } from 'zustand'

import { evaluateRules, type ExtractedParam, type Finding, type Rule } from './engine/rules'

export const CONFIDENCE_THRESHOLD = 0.7

export interface ReviewerAction {
  action?: 'accept' | 'dismiss'
  note?: string
}

export interface SheetPage {
  dataUrl: string // rendered page image (SVG data URL in demo, PNG from pdf.js live)
  width: number
  height: number
}

interface AppState {
  stage: 'upload' | 'workspace'
  rules: Rule[]
  packNames: string[]
  sheet: SheetPage | null
  sheetName: string
  params: ExtractedParam[]
  /** reviewer-typed values for rule inputs the sheet can't provide (ward/LUC limits etc.) */
  supplied: Record<string, number>
  reviewerActions: Record<string, ReviewerAction>
  /** panel focus — param name or finding rule id */
  focusParam: string | null
  tab: 'values' | 'checks'

  setPacks: (rules: Rule[], packNames: string[]) => void
  openReview: (sheetName: string, sheet: SheetPage | null, params: ExtractedParam[]) => void
  setParamValue: (name: string, value: unknown) => void
  setConfirmed: (name: string, confirmed: boolean) => void
  setSupplied: (name: string, value: number | null) => void
  setReviewerAction: (ruleId: string, patch: ReviewerAction) => void
  setFocusParam: (name: string | null) => void
  setTab: (tab: 'values' | 'checks') => void
  reset: () => void
}

export const useStore = create<AppState>((set) => ({
  stage: 'upload',
  rules: [],
  packNames: [],
  sheet: null,
  sheetName: '',
  params: [],
  supplied: {},
  reviewerActions: {},
  focusParam: null,
  tab: 'values',

  setPacks: (rules, packNames) => set({ rules, packNames }),
  openReview: (sheetName, sheet, params) =>
    set({ stage: 'workspace', sheetName, sheet, params, supplied: {}, reviewerActions: {}, focusParam: null, tab: 'values' }),
  setParamValue: (name, value) =>
    set((s) => ({
      params: s.params.map((p) =>
        p.param === name
          ? { ...p, value, editedFrom: p.editedFrom ?? (p.value === value ? undefined : p.value) }
          : p,
      ),
    })),
  setConfirmed: (name, confirmed) =>
    set((s) => ({
      params: s.params.map((p) => (p.param === name ? { ...p, confirmed } : p)),
    })),
  setSupplied: (name, value) =>
    set((s) => {
      const supplied = { ...s.supplied }
      if (value === null || Number.isNaN(value) || value === 0) delete supplied[name]
      else supplied[name] = value
      return { supplied }
    }),
  setReviewerAction: (ruleId, patch) =>
    set((s) => ({
      reviewerActions: { ...s.reviewerActions, [ruleId]: { ...s.reviewerActions[ruleId], ...patch } },
    })),
  setFocusParam: (name) => set({ focusParam: name }),
  setTab: (tab) => set({ tab }),
  reset: () =>
    set({ stage: 'upload', sheet: null, sheetName: '', params: [], supplied: {}, reviewerActions: {}, focusParam: null, tab: 'values' }),
}))

/** All params fed to the engine: extracted + reviewer-supplied limits (confidence 1, confirmed). */
export function effectiveParams(params: ExtractedParam[], supplied: Record<string, number>): ExtractedParam[] {
  const suppliedParams: ExtractedParam[] = Object.entries(supplied).map(([name, value]) => ({
    param: name, value, unit: '', confidence: 1.0,
    sourcePage: 0, sourceCrop: null, bbox: null, confirmed: true,
  }))
  return [...params, ...suppliedParams]
}

/** Live findings with reviewer actions re-applied (findings are recreated every eval). */
export function liveFindings(
  rules: Rule[],
  params: ExtractedParam[],
  supplied: Record<string, number>,
  reviewerActions: Record<string, ReviewerAction>,
): Finding[] {
  return evaluateRules(rules, effectiveParams(params, supplied)).map((f) => ({
    ...f,
    userAction: reviewerActions[f.ruleId]?.action ?? null,
    userNote: reviewerActions[f.ruleId]?.note ?? null,
  }))
}

/** Rule inputs that are neither extracted nor supplied — the reviewer must provide these. */
export function missingInputs(rules: Rule[], params: ExtractedParam[], supplied: Record<string, number>): string[] {
  const have = new Set([...params.map((p) => p.param), ...Object.keys(supplied)])
  const names = new Set<string>()
  for (const r of rules) for (const p of r.parameters) if (!have.has(p)) names.add(p)
  return [...names].sort()
}
