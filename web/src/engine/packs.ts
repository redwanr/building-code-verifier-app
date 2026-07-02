/** Fetch rule packs (static assets synced from ../rule_packs at build). */
import { parsePack, type Rule } from './rules'

export async function fetchPacks(): Promise<{ rules: Rule[]; packNames: string[] }> {
  const base = import.meta.env.BASE_URL
  const index: string[] = await (await fetch(`${base}rule_packs/index.json`)).json()
  const texts = await Promise.all(
    index.map(async (f) => (await fetch(`${base}rule_packs/${f}`)).text()),
  )
  return {
    rules: texts.flatMap(parsePack),
    packNames: index.map((f) => f.replace(/\.yaml$/, '')),
  }
}
