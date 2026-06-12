"""Provider A/B: extraction field accuracy, Claude vs Gemini (PRD §12).

Usage:
  1. Put labeled sheets in fixtures/: <name>.pdf + <name>.truth.yaml
     (truth file: {param_name: ground_truth_value, ...})
  2. export ANTHROPIC_API_KEY=... GEMINI_API_KEY=...
  3. .venv/bin/python eval_providers.py [claude|gemini|both]

Reports raw pre-confirmation accuracy per field (target >= 0.80 on Tier-1).
Numbers exact-match within 1% tolerance; booleans exact.
"""

import os
import sys
import tempfile
from pathlib import Path

import yaml

from extraction import extract_params

FIXTURES = Path(__file__).parent / "fixtures"


def matches(extracted, truth):
    if isinstance(truth, bool) or isinstance(extracted, bool):
        return bool(extracted) == bool(truth)
    try:
        e, t = float(extracted), float(truth)
        return abs(e - t) <= 0.01 * max(abs(t), 1e-9)
    except (TypeError, ValueError):
        return str(extracted).strip() == str(truth).strip()


def run(provider: str):
    key = os.environ["ANTHROPIC_API_KEY" if provider == "claude"
                     else "GEMINI_API_KEY"]
    sheets = sorted(FIXTURES.glob("*.truth.yaml"))
    if not sheets:
        sys.exit("No fixtures found. Add <name>.pdf + <name>.truth.yaml "
                 "to fixtures/.")
    total_correct = total_fields = 0
    for truth_path in sheets:
        pdf_path = truth_path.with_name(
            truth_path.name.replace(".truth.yaml", ".pdf"))
        truth = yaml.safe_load(truth_path.read_text())
        params = {p.param: p for p in extract_params(
            pdf_path.read_bytes(), provider, key, tempfile.mkdtemp())}
        print(f"\n=== {pdf_path.name} · {provider} ===")
        for name, expected in truth.items():
            got = params.get(name)
            ok = got is not None and matches(got.value, expected)
            total_correct += ok
            total_fields += 1
            print(f"  {'✅' if ok else '❌'} {name}: "
                  f"expected {expected}, got "
                  f"{got.value if got else 'MISSING'}"
                  + (f" (conf {got.confidence:.2f})" if got else ""))
    print(f"\n{provider} field accuracy: {total_correct}/{total_fields} "
          f"= {total_correct / total_fields:.2%}")


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "both"
    for prov in (["claude", "gemini"] if arg == "both" else [arg]):
        run(prov)
