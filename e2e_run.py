"""Headless e2e: real PDF -> extraction -> rules -> findings markdown.

Usage: GEMINI_API_KEY=... .venv/bin/python e2e_run.py <pdf> [claude|gemini]
ponytail: throwaway runner, not a pytest test — the pipeline funcs are the product.
"""
import os
import sys
import tempfile

from extraction import extract_params
from rules import evaluate_rules, load_packs, PACK_DIR
from report import new_report, render_markdown

pdf_path = sys.argv[1]
provider = sys.argv[2] if len(sys.argv) > 2 else "gemini"
key = os.environ["ANTHROPIC_API_KEY" if provider == "claude" else "GEMINI_API_KEY"]

with open(pdf_path, "rb") as f:
    pdf_bytes = f.read()

crop_dir = tempfile.mkdtemp(prefix="e2e_crops_")
print(f"provider={provider}  crops={crop_dir}\nextracting...", flush=True)

params = extract_params(pdf_bytes, provider, key, crop_dir)
print(f"\n{len(params)} params extracted:")
for p in sorted(params, key=lambda x: x.param):
    flag = "" if p.confirmed else "  [UNCONFIRMED <0.7]"
    print(f"  {p.param:28} = {p.value!r:>10}  conf={p.confidence:.2f}{flag}")

findings = evaluate_rules(load_packs(), params)
packs = sorted(p.stem for p in PACK_DIR.glob("*.yaml"))
report = new_report(packs, params, findings)

print("\n===== FINDINGS MARKDOWN =====\n")
print(render_markdown(report))
