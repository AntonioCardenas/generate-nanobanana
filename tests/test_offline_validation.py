#!/usr/bin/env python3
"""Offline $0 validation suite for Interactions API request shapes, MIME magic bytes, URI allowlists, and polling deadlines."""

from __future__ import annotations

import json
import mimetypes
import re
import tempfile
import unittest
from pathlib import Path
from urllib.parse import urlparse

SUPPORTED_IMAGE_MIMES = {"image/png", "image/jpeg", "image/webp", "image/heic", "image/heif"}
STANDARD_IMAGE_RATIOS = {"1:1", "16:9", "9:16", "4:3", "3:4", "3:2", "2:3", "4:5", "5:4", "21:9"}
PANORAMIC_2_1_RATIOS = STANDARD_IMAGE_RATIOS | {"1:4", "4:1", "1:8", "8:1"}


def detect_image_mime(path: str | Path) -> str:
    p = Path(path)
    if not p.is_file() or p.stat().st_size == 0:
        raise ValueError(f"Reference image missing or empty: {p}")
    header = p.read_bytes()[:12]
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if header.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        return "image/webp"
    if header[4:8] == b"ftyp":
        brand = header[8:12]
        if brand in {b"heic", b"heix", b"mif1"}:
            return "image/heic"
        if brand in {b"heif", b"msf1"}:
            return "image/heif"
    guessed, _ = mimetypes.guess_type(str(p))
    if guessed in SUPPORTED_IMAGE_MIMES:
        return guessed
    raise ValueError(f"Unsupported image MIME ({guessed}) for {p}")


def validate_interaction_request(payload: dict) -> None:
    if not isinstance(payload, dict):
        raise ValueError("Request payload must be a dict.")
    if "reference_images" in payload:
        raise ValueError("Invalid top-level 'reference_images' key: pass {'type': 'image', ...} blocks inside 'input'.")

    model = payload.get("model", "")
    inp = payload.get("input")
    if not inp or not isinstance(inp, (str, list)):
        raise ValueError("'input' must be a non-empty string or list of content parts.")

    image_parts = []
    if isinstance(inp, list):
        for idx, part in enumerate(inp):
            if not isinstance(part, dict) or "type" not in part:
                raise ValueError(f"input[{idx}] must be a dict with a 'type' field.")
            if part["type"] == "image":
                if part.get("mime_type") not in SUPPORTED_IMAGE_MIMES:
                    raise ValueError(f"input[{idx}] has unsupported or missing mime_type: {part.get('mime_type')}")
                if not part.get("data") and not part.get("uri"):
                    raise ValueError(f"input[{idx}] image part requires 'data' (base64) or 'uri'.")
                image_parts.append(part)

    rf = payload.get("response_format") or {}
    gc = payload.get("generation_config") or {}
    for deprecated in ("temperature", "top_p", "top_k", "thinking_budget"):
        if deprecated in gc:
            raise ValueError(f"Unsupported/deprecated generation_config field: '{deprecated}'.")

    if model == "gemini-3.1-flash-lite-image":
        if rf.get("type") != "image" or rf.get("image_size", "1K") != "1K":
            raise ValueError("gemini-3.1-flash-lite-image requires response_format.type='image' and image_size='1K' only.")
        if rf.get("aspect_ratio", "1:1") not in STANDARD_IMAGE_RATIOS:
            raise ValueError(f"Unsupported aspect_ratio on Lite: {rf.get('aspect_ratio')}")
        if len(image_parts) > 2:
            raise ValueError("Keep Nano Banana 2 Lite drafting inputs to 0-2 reference images.")
        if gc.get("thinking_level", "minimal") not in {"minimal", "high"}:
            raise ValueError("Lite supports thinking_level 'minimal' or 'high' only.")
    elif model == "gemini-nano-banana-2.1":
        if rf.get("type") != "image" or rf.get("image_size", "1K") not in {"1K", "2K", "4K"}:
            raise ValueError("gemini-nano-banana-2.1 requires response_format.type='image' and image_size in {'1K','2K','4K'}.")
        if rf.get("aspect_ratio", "1:1") not in PANORAMIC_2_1_RATIOS:
            raise ValueError(f"Unsupported aspect_ratio on Nano Banana 2.1: {rf.get('aspect_ratio')}")
        if len(image_parts) > 14:
            raise ValueError("gemini-nano-banana-2.1 accepts at most 14 image parts in input.")
        if gc.get("thinking_level", "medium") not in {"minimal", "medium", "high"}:
            raise ValueError("Nano Banana 2.1 supports thinking_level in {'minimal','medium','high'}.")
    elif model == "gemini-3-pro-image":
        if rf.get("type") != "image" or rf.get("image_size", "2K") not in {"1K", "2K", "4K"}:
            raise ValueError("gemini-3-pro-image requires response_format.type='image' and image_size in {'1K','2K','4K'}.")
        if rf.get("aspect_ratio", "1:1") not in STANDARD_IMAGE_RATIOS:
            raise ValueError(f"Unsupported aspect_ratio on Nano Banana Pro (panoramic 1:4/8:1 requires 2.1): {rf.get('aspect_ratio')}")
        if len(image_parts) > 14:
            raise ValueError("gemini-3-pro-image accepts at most 14 image parts in input.")
    elif model == "gemini-omni-1.2-flash":
        if rf and rf.get("type", "video") != "video":
            raise ValueError("gemini-omni-1.2-flash outputs video only.")
        if rf.get("resolution", "720p") not in {"360p", "720p", "1080p", "4k"}:
            raise ValueError(f"Unsupported Omni resolution: {rf.get('resolution')}")
        if rf.get("aspect_ratio", "16:9") not in {"16:9", "9:16"}:
            raise ValueError(f"Unsupported Omni aspect_ratio: {rf.get('aspect_ratio')}")
        if len(image_parts) > 6:
            raise ValueError("gemini-omni-1.2-flash accepts at most 6 image parts in input.")
    elif model in {"gemini-4-hydrogen", "gemini-4-neon", "gemini-4-argon", "gemini-4-carbon"}:
        if rf.get("type") in {"image", "video"}:
            raise ValueError(f"{model} outputs text/code only, not raster image or video.")
        allowed_thinking = {"low", "medium", "high", "xhigh"} if model in {"gemini-4-hydrogen", "gemini-4-neon"} else {"low", "medium", "high"}
        if gc.get("thinking_level", "medium") not in allowed_thinking:
            raise ValueError(f"Invalid thinking_level '{gc.get('thinking_level')}' for {model} (allowed: {sorted(allowed_thinking)}).")
    else:
        raise ValueError(f"Unrecognized model route: {model}")


def parse_verified_file_name(uri: str) -> str:
    parsed = urlparse(uri or "")
    if parsed.scheme != "https" or parsed.hostname != "generativelanguage.googleapis.com" or parsed.query or parsed.fragment:
        raise ValueError(f"Untrusted or non-canonical delivery URI: {uri}")
    match = re.fullmatch(r"/(?:v1(?:beta)?/)?(files/[a-z0-9-]+)", parsed.path)
    if not match:
        raise ValueError(f"Invalid Files API resource path in URI: {uri}")
    return match.group(1)


def simulate_bounded_poll(states: list[str], deadline_seconds: int, step_seconds: int) -> str:
    elapsed = 0
    for state in states:
        if state == "ACTIVE":
            return "ACTIVE"
        if state == "FAILED":
            raise RuntimeError("Video generation failed on Files API.")
        elapsed += step_seconds
        if elapsed >= deadline_seconds:
            raise TimeoutError("Timed out waiting for Files API resource.")
    raise TimeoutError("Timed out waiting for Files API resource.")


class OfflineValidationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parent.parent
        cls.req_fixtures = json.loads((root / "references/fixtures/offline-request-fixtures.json").read_text(encoding="utf-8"))
        cls.uri_fixtures = json.loads((root / "references/fixtures/offline-timeout-uri-fixtures.json").read_text(encoding="utf-8"))

    def test_valid_request_fixtures(self):
        for case in self.req_fixtures["valid_requests"]:
            with self.subTest(case=case["id"]):
                validate_interaction_request(case["payload"])

    def test_invalid_request_fixtures(self):
        for case in self.req_fixtures["invalid_requests"]:
            with self.subTest(case=case["id"]):
                with self.assertRaises(ValueError) as ctx:
                    validate_interaction_request(case["payload"])
                self.assertIn(case["expected_error"], str(ctx.exception))

    def test_uri_allowlist_fixtures(self):
        for case in self.uri_fixtures["uri_cases"]:
            with self.subTest(case=case["id"]):
                if case["valid"]:
                    self.assertEqual(parse_verified_file_name(case["uri"]), case["expected_resource"])
                else:
                    with self.assertRaises(ValueError):
                        parse_verified_file_name(case["uri"])

    def test_mime_magic_byte_fixtures(self):
        with tempfile.TemporaryDirectory() as tmp:
            for case in self.uri_fixtures["mime_magic_cases"]:
                with self.subTest(case=case["id"]):
                    fpath = Path(tmp) / case["filename"]
                    fpath.write_bytes(bytes.fromhex(case["hex_prefix"]))
                    self.assertEqual(detect_image_mime(fpath), case["expected_mime"])

    def test_bounded_polling_timeout_fixtures(self):
        for case in self.uri_fixtures["polling_timeout_cases"]:
            with self.subTest(case=case["id"]):
                outcome = case["expected_outcome"]
                if outcome == "ACTIVE":
                    self.assertEqual(
                        simulate_bounded_poll(case["simulated_states"], case["deadline_seconds"], case["step_seconds"]),
                        "ACTIVE",
                    )
                elif outcome == "RuntimeError":
                    with self.assertRaises(RuntimeError):
                        simulate_bounded_poll(case["simulated_states"], case["deadline_seconds"], case["step_seconds"])
                elif outcome == "TimeoutError":
                    with self.assertRaises(TimeoutError):
                        simulate_bounded_poll(case["simulated_states"], case["deadline_seconds"], case["step_seconds"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
