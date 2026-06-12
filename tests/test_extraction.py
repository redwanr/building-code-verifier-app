"""Extraction post-processing tests — written before implementation (TDD).

The LLM call itself is exercised by the live provider A/B (task 5); these
tests cover the deterministic parts: response parsing, the FR-4 confidence
gate, and best-effort bbox crop rendering with page fallback.
"""

from PIL import Image

from extraction import params_from_response, render_crop, CONFIDENCE_THRESHOLD


SAMPLE_RESPONSE = {
    "params": [
        {"param": "claimed_far", "value": 4.2, "unit": "ratio",
         "confidence": 0.62, "bbox": [100, 200, 300, 250],
         "location_note": "FAR row of the area statement table"},
        {"param": "num_storeys", "value": 10, "unit": "count",
         "confidence": 0.95, "bbox": None,
         "location_note": "title block, building description"},
    ]
}


def _page(tmp_path, w=1000, h=800):
    img = Image.new("RGB", (w, h), "white")
    path = tmp_path / "page1.png"
    img.save(path)
    return img


def test_params_parsed_with_confidence_gate(tmp_path):
    page = _page(tmp_path)
    params = params_from_response(SAMPLE_RESPONSE, page, source_page=1,
                                  crop_dir=tmp_path)
    by_name = {p.param: p for p in params}
    assert by_name["claimed_far"].value == 4.2
    # FR-4: below threshold -> unconfirmed, needs human confirmation
    assert by_name["claimed_far"].confirmed is False
    # at/above threshold -> pre-confirmed
    assert by_name["num_storeys"].confirmed is True
    assert CONFIDENCE_THRESHOLD == 0.7


def test_bbox_produces_crop_file(tmp_path):
    page = _page(tmp_path)
    params = params_from_response(SAMPLE_RESPONSE, page, source_page=1,
                                  crop_dir=tmp_path)
    far = next(p for p in params if p.param == "claimed_far")
    assert far.source_crop is not None
    crop = Image.open(far.source_crop)
    # padded crop: larger than raw bbox (200x50), smaller than full page
    assert crop.width > 200 and crop.width < 1000


def test_missing_bbox_falls_back_to_location_note(tmp_path):
    page = _page(tmp_path)
    params = params_from_response(SAMPLE_RESPONSE, page, source_page=1,
                                  crop_dir=tmp_path)
    storeys = next(p for p in params if p.param == "num_storeys")
    assert storeys.source_crop is None
    assert "title block" in storeys.crop_fallback_note


def test_garbage_bbox_falls_back(tmp_path):
    page = _page(tmp_path)
    crop = render_crop(page, [5000, 5000, 6000, 6000], tmp_path, "x")
    assert crop is None  # out of bounds -> fallback, never crash
