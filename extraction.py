"""PDF rasterization + vision-LLM parameter extraction (PRD §8).

Vision-LLM only (no OCR engine) — one call per page with the full params
schema. Provider-switched: Claude Opus 4.8 (default) or Gemini, same prompt
and JSON schema both sides so the G+9 eval compares like for like.
"""

from __future__ import annotations

import json
import os
from io import BytesIO
from pathlib import Path

from PIL import Image

from report import ExtractedParam

CONFIDENCE_THRESHOLD = 0.7  # FR-4: below this -> human confirmation required
DPI = 200
CROP_PAD = 40  # px padding around bbox — vision bboxes are approximate

CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-opus-4-8")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")

# Tier-1 table/text params (PRD §4). Geometry reads are out of MVP.
PARAM_NAMES = [
    "building_height_m", "num_storeys", "plot_area_m2", "total_floor_area_m2",
    "claimed_far", "claimed_mgc_pct",
    "num_exit_stairs", "exit_stair_width_m", "num_lifts",
    "parking_provided", "parking_provided_table", "parking_count_on_plan",
    "num_units",
    "front_setback_m", "rear_setback_m", "side_setback_m",
    "has_fire_alarm", "has_fire_hydrant_standpipe",
    "has_fire_rated_stair_enclosure", "has_firefighting_lift",
]

# (param, value, unit, confidence) — representative G+9 sheet for offline UI
# testing. Mix of confidences so the confirmation gate and all three finding
# buckets get exercised. No API call, no credits.
_MOCK_ROWS = [
    ("building_height_m", 35.0, "m", 0.80),
    ("num_storeys", 10, "", 0.95),
    ("plot_area_m2", 200.0, "m²", 0.90),
    ("total_floor_area_m2", 840.0, "m²", 0.88),
    ("claimed_far", 4.2, "", 0.62),             # flagged
    ("claimed_mgc_pct", 58.0, "%", 0.88),
    ("num_exit_stairs", 1, "", 0.55),           # flagged
    ("exit_stair_width_m", 1.2, "m", 0.72),
    ("num_lifts", 2, "", 0.90),
    ("parking_provided", 8, "", 0.90),
    ("parking_provided_table", 8, "", 0.86),
    ("parking_count_on_plan", 6, "", 0.84),     # mismatch → red finding
    ("num_units", 36, "", 0.84),
    ("front_setback_m", 1.5, "m", 0.78),
    ("rear_setback_m", 1.0, "m", 0.66),         # flagged
    ("side_setback_m", 1.25, "m", 0.74),
    ("has_fire_alarm", True, "", 0.58),         # flagged
    ("has_fire_hydrant_standpipe", False, "", 0.80),
    ("has_fire_rated_stair_enclosure", True, "", 0.83),
    ("has_firefighting_lift", False, "", 0.77),
]


def mock_params() -> list[ExtractedParam]:
    """Canned extraction for local UI testing — bypasses the vision-LLM call."""
    return [
        ExtractedParam(param=p, value=v, unit=u, confidence=c, source_page=1,
                       crop_fallback_note="mock fixture — no crop")
        for p, v, u, c in _MOCK_ROWS
    ]


EXTRACTION_PROMPT = f"""You are reading one page of a RAJUK building-approval permit sheet \
(Dhaka, Bangladesh): a dense raster drawing with floor plans, elevations, sections, \
and data tables (area/FAR/MGC/setback/parking). Labels are mostly English; some \
Bangla may appear in tables.

Extract ONLY values you can actually see printed as text/table values or count \
directly (e.g. number of stair cores, lifts, parking spots drawn). NEVER guess or \
infer a value that is not on the page. Target parameters:
{json.dumps(PARAM_NAMES, indent=2)}

Return JSON exactly in this shape:
{{"params": [{{
  "param": "<name from the list>",
  "value": <number or boolean>,
  "unit": "<m | m2 | ratio | percent | count | bool>",
  "confidence": <0.0-1.0, your honest confidence in this exact reading>,
  "bbox": [x0, y0, x1, y1] or null,   // pixel coords on THIS image; null if unsure
  "location_note": "<where on the sheet this value appears>"
}}]}}

Rules:
- Omit any parameter not visible on this page. An omitted param is better than a guess.
- has_* params: true only if the provision is explicitly shown/noted; omit otherwise.
- parking_provided_table = the number stated in the parking table; \
parking_count_on_plan = spots you can count drawn on the plan. Report both if visible.
- Convert feet to metres where units are imperial; note the conversion in location_note.
- Be conservative with confidence: dense/blurry/ambiguous reads get < 0.7."""


# --- rasterize ---

def rasterize(pdf_bytes: bytes, dpi: int = DPI) -> list[Image.Image]:
    from pdf2image import convert_from_bytes
    return convert_from_bytes(pdf_bytes, dpi=dpi)


# --- response post-processing (deterministic, unit-tested) ---

def render_crop(page: Image.Image, bbox, crop_dir, name) -> str | None:
    """Padded crop for the audit trail. Garbage bbox -> None (page fallback)."""
    try:
        x0, y0, x1, y1 = (float(v) for v in bbox)
    except (TypeError, ValueError):
        return None
    if not (0 <= x0 < x1 <= page.width and 0 <= y0 < y1 <= page.height):
        return None
    box = (max(0, x0 - CROP_PAD), max(0, y0 - CROP_PAD),
           min(page.width, x1 + CROP_PAD), min(page.height, y1 + CROP_PAD))
    path = Path(crop_dir) / f"{name}.png"
    page.crop(box).save(path)
    return str(path)


def params_from_response(response: dict, page: Image.Image, source_page: int,
                         crop_dir) -> list[ExtractedParam]:
    params = []
    for row in response.get("params", []):
        confidence = float(row.get("confidence", 0.0))
        crop = render_crop(page, row.get("bbox"), crop_dir,
                           f"{row['param']}_p{source_page}")
        params.append(ExtractedParam(
            param=row["param"], value=row["value"], unit=row.get("unit", ""),
            confidence=confidence, source_page=source_page,
            source_crop=crop,
            crop_fallback_note=None if crop else row.get("location_note"),
            confirmed=confidence >= CONFIDENCE_THRESHOLD,
        ))
    return params


# --- provider calls ---

def _png_bytes(page: Image.Image) -> bytes:
    buf = BytesIO()
    page.save(buf, format="PNG")
    return buf.getvalue()


_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "params": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "param": {"type": "string", "enum": PARAM_NAMES},
                    "value": {"anyOf": [{"type": "number"}, {"type": "boolean"}]},
                    "unit": {"type": "string"},
                    "confidence": {"type": "number"},
                    "bbox": {"anyOf": [
                        {"type": "array", "items": {"type": "number"}},
                        {"type": "null"},
                    ]},
                    "location_note": {"type": "string"},
                },
                "required": ["param", "value", "unit", "confidence",
                             "bbox", "location_note"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["params"],
    "additionalProperties": False,
}


def _call_claude(page: Image.Image, api_key: str) -> dict:
    import anthropic
    import base64

    client = anthropic.Anthropic(api_key=api_key)
    with client.messages.stream(
        model=CLAUDE_MODEL,
        max_tokens=16000,
        output_config={"format": {"type": "json_schema",
                                  "schema": _RESPONSE_SCHEMA}},
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {
                    "type": "base64", "media_type": "image/png",
                    "data": base64.standard_b64encode(_png_bytes(page)).decode(),
                }},
                {"type": "text", "text": EXTRACTION_PROMPT},
            ],
        }],
    ) as stream:
        message = stream.get_final_message()
    if message.stop_reason == "refusal":
        raise RuntimeError("Claude declined the request (refusal stop reason).")
    text = next(b.text for b in message.content if b.type == "text")
    return json.loads(text)


def _call_gemini(page: Image.Image, api_key: str) -> dict:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[
            types.Part.from_bytes(data=_png_bytes(page), mime_type="image/png"),
            EXTRACTION_PROMPT,
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
        ),
    )
    return json.loads(response.text)


_PROVIDERS = {"claude": _call_claude, "gemini": _call_gemini}


def extract_params(pdf_bytes: bytes, provider: str, api_key: str,
                   crop_dir) -> list[ExtractedParam]:
    """Full pipeline: rasterize -> per-page vision call -> ExtractedParam list."""
    call = _PROVIDERS[provider]
    params: list[ExtractedParam] = []
    for page_num, page in enumerate(rasterize(pdf_bytes), start=1):
        response = call(page, api_key)
        params.extend(params_from_response(response, page, page_num, crop_dir))
    # keep the highest-confidence read when the same param appears on >1 page
    best: dict[str, ExtractedParam] = {}
    for p in params:
        if p.param not in best or p.confidence > best[p.param].confidence:
            best[p.param] = p
    return list(best.values())
