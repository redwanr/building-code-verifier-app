"""Headless e2e: real PDF -> extraction -> rules -> findings markdown.

Usage: GEMINI_API_KEY=... .venv/bin/python e2e_run.py <pdf> [claude|gemini]
Writes raw LLM JSON + per-param crops to ./e2e_out/ for inspection.
ponytail: throwaway runner, not a pytest test — the pipeline funcs are the product.
"""
import json
import os
import sys
from pathlib import Path

from extraction import (rasterize, params_from_response, _PROVIDERS)
from rules import evaluate_rules, load_packs, PACK_DIR
from report import new_report, render_markdown

pdf_path = sys.argv[1]
provider = sys.argv[2] if len(sys.argv) > 2 else "gemini"
key = os.environ["ANTHROPIC_API_KEY" if provider == "claude" else "GEMINI_API_KEY"]
call = _PROVIDERS[provider]

out = Path("e2e_out")
crops = out / "crops"
crops.mkdir(parents=True, exist_ok=True)

with open(pdf_path, "rb") as f:
    pdf_bytes = f.read()

print(f"provider={provider}  out={out}/\nextracting...", flush=True)

params = []
for page_num, page in enumerate(rasterize(pdf_bytes), start=1):
    response = call(page, key)                       # raw LLM JSON
    raw_path = out / f"raw_p{page_num}.json"
    raw_path.write_text(json.dumps(response, indent=2))
    print(f"  raw -> {raw_path}")
    params.extend(params_from_response(response, page, page_num, crops))

# keep highest-confidence read per param (same as extract_params)
best = {}
for p in params:
    if p.param not in best or p.confidence > best[p.param].confidence:
        best[p.param] = p
params = list(best.values())

print(f"\n{len(params)} params extracted (crops in {crops}/):")
for p in sorted(params, key=lambda x: x.param):
    flag = "" if p.confirmed else "  [UNCONFIRMED <0.7]"
    crop = Path(p.source_crop).name if p.source_crop else f"(no crop: {p.crop_fallback_note})"
    print(f"  {p.param:28} = {p.value!r:>10}  conf={p.confidence:.2f}{flag}  {crop}")

findings = evaluate_rules(load_packs(), params)
packs = sorted(p.stem for p in PACK_DIR.glob("*.yaml"))
report = new_report(packs, params, findings)
md_path = out / "findings.md"
md_path.write_text(render_markdown(report))
print(f"\nfindings markdown -> {md_path}")
