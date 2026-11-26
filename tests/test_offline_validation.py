#!/usr/bin/env python3
"""Offline $0 validation & stubbed-SDK regression suite for request shapes, MIME magic bytes, URI allowlists, and end-to-end bounded retrieval."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
import json
import math
import mimetypes
import os
import re
import tempfile
import time
from types import SimpleNamespace
from typing import Any, Callable
import unittest
import uuid
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


def remaining_timeout_ms(deadline: float, *, clock: Callable[[], float] = time.monotonic) -> int:
    remaining_s = deadline - clock()
    if remaining_s <= 0:
        raise TimeoutError("End-to-end deadline exceeded before SDK call.")
    return max(1, math.ceil(remaining_s * 1000))


def call_with_remaining_budget(
    fn: Callable[[Any], Any],
    *,
    deadline: float,
    client_factory: Callable[[int], Any],
    clock: Callable[[], float] = time.monotonic,
    enforce_wall_timeout: bool | None = None,
) -> Any:
    timeout_ms = remaining_timeout_ms(deadline, clock=clock)
    remaining_s = timeout_ms / 1000.0
    if enforce_wall_timeout is None:
        enforce_wall_timeout = clock is time.monotonic

    scoped_client = client_factory(timeout_ms)
    close_fn = getattr(scoped_client, "close", None)
    if enforce_wall_timeout:
        pool = ThreadPoolExecutor(max_workers=1)
        future = pool.submit(fn, scoped_client)
        try:
            result = future.result(timeout=remaining_s)
        except FuturesTimeoutError as exc:
            future.cancel()
            if callable(close_fn):
                close_fn()
            raise TimeoutError(f"SDK call exceeded remaining {remaining_s:.3f}s budget.") from exc
        finally:
            pool.shutdown(wait=False, cancel_futures=True)
        if callable(close_fn):
            close_fn()
    else:
        try:
            result = fn(scoped_client)
        finally:
            if callable(close_fn):
                close_fn()

    if clock() > deadline:
        raise TimeoutError("SDK call finished after end-to-end deadline expired.")
    return result


def atomic_write_verified_bytes(
    output_path: str | Path,
    payload: bytes,
    *,
    deadline: float,
    clock: Callable[[], float] = time.monotonic,
    overwrite: bool = False,
) -> Path:
    out = Path(output_path)
    if out.is_symlink():
        raise RuntimeError(f"Refusing symlink destination: {out}")
    if out.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite existing artifact: {out}")
    if not payload:
        raise RuntimeError(f"Refusing to save empty output payload: {out}")

    out.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = out.parent / f".{out.name}.{uuid.uuid4().hex}.part"
    committed = False
    try:
        tmp_path.write_bytes(payload)
        if clock() > deadline:
            raise TimeoutError(f"Deadline expired before committing {out}; cleaned up staging file.")
        if out.exists() and not overwrite:
            raise FileExistsError(f"Destination appeared concurrently: {out}")
        os.replace(tmp_path, out)
        committed = True
        return out
    finally:
        if not committed and tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


def retrieve_uri_media_bounded(
    *,
    create_kwargs: dict[str, Any],
    output_path: str | Path,
    total_budget_s: float = 600.0,
    poll_interval_s: float = 5.0,
    client_factory: Callable[[int], Any],
    clock: Callable[[], float] = time.monotonic,
    sleep_fn: Callable[[float], None] = time.sleep,
    overwrite: bool = False,
) -> tuple[str, Path]:
    if total_budget_s <= 0:
        raise ValueError("total_budget_s must be > 0")
    out = Path(output_path)
    if out.is_symlink():
        raise RuntimeError(f"Refusing symlink destination: {out}")
    if out.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite existing artifact: {out}")

    deadline = clock() + total_budget_s
    interaction = call_with_remaining_budget(
        lambda c: c.interactions.create(**create_kwargs),
        deadline=deadline,
        client_factory=client_factory,
        clock=clock,
    )
    interaction_id = getattr(interaction, "id", None) or "unknown"
    video_out = getattr(interaction, "output_video", None)
    if video_out is None or not getattr(video_out, "uri", None):
        raise RuntimeError(f"Missing output_video.uri (interaction={interaction_id}).")

    resource_name = parse_verified_file_name(video_out.uri)
    while True:
        f_info = call_with_remaining_budget(
            lambda c: c.files.get(name=resource_name),
            deadline=deadline,
            client_factory=client_factory,
            clock=clock,
        )
        state = getattr(getattr(f_info, "state", None), "name", getattr(f_info, "state", None))
        if state == "ACTIVE":
            break
        if state == "FAILED":
            raise RuntimeError(f"Files API processing failed for {resource_name} (interaction={interaction_id}).")
        remaining_s = deadline - clock()
        if remaining_s <= 0:
            raise TimeoutError(
                f"Timed out polling {resource_name} (interaction={interaction_id}); reconcile remote status before rerunning."
            )
        sleep_fn(min(poll_interval_s, remaining_s))

    media_bytes = call_with_remaining_budget(
        lambda c: c.files.download(file=resource_name),
        deadline=deadline,
        client_factory=client_factory,
        clock=clock,
    )
    saved = atomic_write_verified_bytes(out, media_bytes, deadline=deadline, clock=clock, overwrite=overwrite)
    return interaction_id, saved


def poll_background_interaction_bounded(
    *,
    create_kwargs: dict[str, Any],
    output_path: str | Path,
    total_budget_s: float = 900.0,
    poll_interval_s: float = 5.0,
    client_factory: Callable[[int], Any],
    clock: Callable[[], float] = time.monotonic,
    sleep_fn: Callable[[float], None] = time.sleep,
    overwrite: bool = False,
) -> tuple[str, Path]:
    if total_budget_s <= 0:
        raise ValueError("total_budget_s must be > 0")
    deadline = clock() + total_budget_s
    interaction = call_with_remaining_budget(
        lambda c: c.interactions.create(**{**create_kwargs, "background": True}),
        deadline=deadline,
        client_factory=client_factory,
        clock=clock,
    )
    interaction_id = getattr(interaction, "id", None) or "unknown"
    while getattr(interaction, "status", None) in ("in_progress", "queued"):
        remaining_s = deadline - clock()
        if remaining_s <= 0:
            raise TimeoutError(f"Long decode timed out (interaction={interaction_id}); reconcile status before rerunning.")
        sleep_fn(min(poll_interval_s, remaining_s))
        interaction = call_with_remaining_budget(
            lambda c: c.interactions.get(id=interaction_id),
            deadline=deadline,
            client_factory=client_factory,
            clock=clock,
        )
    if getattr(interaction, "status", None) != "completed":
        raise RuntimeError(f"Background interaction failed: status={getattr(interaction, 'status', None)!r}")
    steps = getattr(interaction, "steps", None) or []
    full_text = "".join(
        part.text
        for step in steps
        if getattr(step, "type", None) == "model_output"
        for part in (getattr(step, "content", None) or [])
        if getattr(part, "type", None) == "text" and getattr(part, "text", None)
    ) or (getattr(interaction, "output_text", None) or "")
    saved = atomic_write_verified_bytes(output_path, full_text.encode("utf-8"), deadline=deadline, clock=clock, overwrite=overwrite)
    return interaction_id, saved


class VirtualClock:
    def __init__(self) -> None:
        self.now = 100.0
        self.sleeps: list[float] = []

    def __call__(self) -> float:
        return self.now

    def advance(self, dt: float) -> None:
        self.now += dt

    def sleep(self, dt: float) -> None:
        self.sleeps.append(dt)
        self.now += dt


class StubGenAIHarness:
    """Offline stubbed google-genai harness recording per-call HttpOptions(timeout=ms) and close() cleanup."""

    def __init__(self, case: dict[str, Any], clock: VirtualClock) -> None:
        self.case = case
        self.clock = clock
        self.poll_idx = 0
        self.recorded_calls: list[tuple[str, int]] = []
        self.closed_clients = 0
        self.download_called = False

    def make_client(self, timeout_ms: int) -> Any:
        harness = self

        class _Interactions:
            def create(self, **_kwargs: Any) -> Any:
                harness.recorded_calls.append(("interactions.create", timeout_ms))
                latency_ms = harness.case["create_latency_s"] * 1000.0
                if latency_ms > timeout_ms:
                    harness.clock.advance(timeout_ms / 1000.0)
                    raise TimeoutError("Stubbed transport timeout in interactions.create")
                harness.clock.advance(harness.case["create_latency_s"])
                return SimpleNamespace(
                    id="v1_stub_interaction",
                    output_video=SimpleNamespace(uri=harness.case["uri"]),
                )

        class _Files:
            def get(self, *, name: str) -> Any:
                harness.recorded_calls.append(("files.get", timeout_ms))
                step = harness.case["poll_steps"][min(harness.poll_idx, len(harness.case["poll_steps"]) - 1)]
                harness.poll_idx += 1
                if step["latency_s"] * 1000.0 > timeout_ms:
                    harness.clock.advance(timeout_ms / 1000.0)
                    raise TimeoutError(f"Stubbed transport timeout in files.get({name})")
                harness.clock.advance(step["latency_s"])
                return SimpleNamespace(name=name, state=SimpleNamespace(name=step["state"]))

            def download(self, *, file: str) -> bytes:
                harness.download_called = True
                harness.recorded_calls.append(("files.download", timeout_ms))
                if harness.case["download_latency_s"] * 1000.0 > timeout_ms:
                    harness.clock.advance(timeout_ms / 1000.0)
                    raise TimeoutError(f"Stubbed transport timeout in files.download({file})")
                harness.clock.advance(harness.case["download_latency_s"])
                return bytes.fromhex(harness.case["download_hex"])

        class _Client:
            def __init__(self) -> None:
                self.interactions = _Interactions()
                self.files = _Files()

            def close(self) -> None:
                harness.closed_clients += 1

        return _Client()


class OfflineValidationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        root = Path(__file__).resolve().parent.parent
        cls.req_fixtures = json.loads((root / "references/fixtures/offline-request-fixtures.json").read_text(encoding="utf-8"))
        cls.uri_fixtures = json.loads((root / "references/fixtures/offline-timeout-uri-fixtures.json").read_text(encoding="utf-8"))

    def test_valid_request_fixtures(self) -> None:
        for case in self.req_fixtures["valid_requests"]:
            with self.subTest(case=case["id"]):
                validate_interaction_request(case["payload"])

    def test_invalid_request_fixtures(self) -> None:
        for case in self.req_fixtures["invalid_requests"]:
            with self.subTest(case=case["id"]):
                with self.assertRaises(ValueError) as ctx:
                    validate_interaction_request(case["payload"])
                self.assertIn(case["expected_error"], str(ctx.exception))

    def test_uri_allowlist_fixtures(self) -> None:
        for case in self.uri_fixtures["uri_cases"]:
            with self.subTest(case=case["id"]):
                if case["valid"]:
                    self.assertEqual(parse_verified_file_name(case["uri"]), case["expected_resource"])
                else:
                    with self.assertRaises(ValueError):
                        parse_verified_file_name(case["uri"])

    def test_mime_magic_byte_fixtures(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            for case in self.uri_fixtures["mime_magic_cases"]:
                with self.subTest(case=case["id"]):
                    fpath = Path(tmp) / case["filename"]
                    fpath.write_bytes(bytes.fromhex(case["hex_prefix"]))
                    self.assertEqual(detect_image_mime(fpath), case["expected_mime"])

    def test_stubbed_sdk_bounded_retrieval_regressions(self) -> None:
        for case in self.uri_fixtures["bounded_retrieval_regression_cases"]:
            with self.subTest(case=case["id"]), tempfile.TemporaryDirectory() as tmp:
                tmp_dir = Path(tmp)
                out_mp4 = tmp_dir / "hero_loop.mp4"
                clock = VirtualClock()
                harness = StubGenAIHarness(case, clock)
                outcome = case["expected_outcome"]

                if outcome == "SUCCESS":
                    interaction_id, saved = retrieve_uri_media_bounded(
                        create_kwargs={"model": "gemini-omni-1.2-flash", "input": "test"},
                        output_path=out_mp4,
                        total_budget_s=case["total_budget_s"],
                        poll_interval_s=case["poll_interval_s"],
                        client_factory=harness.make_client,
                        clock=clock,
                        sleep_fn=clock.sleep,
                    )
                    self.assertEqual(interaction_id, "v1_stub_interaction")
                    self.assertTrue(saved.is_file() and saved.stat().st_size > 0)
                    # Verify every call received strictly decreasing remaining timeout_ms
                    timeouts = [ms for _, ms in harness.recorded_calls]
                    self.assertEqual(timeouts, sorted(timeouts, reverse=True))
                    dl_timeout = dict(harness.recorded_calls)["files.download"]
                    self.assertLessEqual(dl_timeout, case["expected_download_timeout_ms_max"])
                else:
                    exc_cls = TimeoutError if outcome == "TimeoutError" else RuntimeError
                    with self.assertRaises(exc_cls):
                        retrieve_uri_media_bounded(
                            create_kwargs={"model": "gemini-omni-1.2-flash", "input": "test"},
                            output_path=out_mp4,
                            total_budget_s=case["total_budget_s"],
                            poll_interval_s=case["poll_interval_s"],
                            client_factory=harness.make_client,
                            clock=clock,
                            sleep_fn=clock.sleep,
                        )
                    self.assertFalse(out_mp4.exists(), "Failed/timed-out retrieval must not commit output file")
                    if "expect_download_called" in case:
                        self.assertEqual(harness.download_called, case["expect_download_called"])
                    if "expected_download_timeout_ms_max" in case:
                        dl_timeout = dict(harness.recorded_calls)["files.download"]
                        self.assertLessEqual(dl_timeout, case["expected_download_timeout_ms_max"])

                # Every scoped client must be closed and zero .part staging files may remain
                self.assertEqual(harness.closed_clients, len(harness.recorded_calls))
                self.assertEqual(list(tmp_dir.glob("*.part")), [])

    def test_real_wall_clock_hung_download_preemption_and_cleanup(self) -> None:
        """Verify a hung SDK download ignoring HttpOptions is preempted at wall-clock deadline and cleans up."""
        closed = []

        def hung_client_factory(timeout_ms: int) -> Any:
            class _Interactions:
                def create(self, **_kw: Any) -> Any:
                    return SimpleNamespace(
                        id="v1_wall_test",
                        output_video=SimpleNamespace(uri="https://generativelanguage.googleapis.com/v1/files/hung123"),
                    )

            class _Files:
                def get(self, *, name: str) -> Any:
                    return SimpleNamespace(name=name, state=SimpleNamespace(name="ACTIVE"))

                def download(self, *, file: str) -> bytes:
                    # Simulate a hung socket ignoring HttpOptions(timeout=timeout_ms)
                    time.sleep(0.35)
                    return b"late-bytes"

            return SimpleNamespace(
                interactions=_Interactions(),
                files=_Files(),
                close=lambda: closed.append(timeout_ms),
            )

        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            out_mp4 = tmp_dir / "hung_video.mp4"
            start = time.monotonic()
            with self.assertRaises(TimeoutError):
                retrieve_uri_media_bounded(
                    create_kwargs={"model": "gemini-omni-1.2-flash", "input": "test"},
                    output_path=out_mp4,
                    total_budget_s=0.07,
                    poll_interval_s=0.02,
                    client_factory=hung_client_factory,
                )
            elapsed = time.monotonic() - start
            self.assertLess(elapsed, 0.25, "Wall-clock guard must preempt hung download well before 0.35s sleep")
            self.assertFalse(out_mp4.exists())
            self.assertEqual(list(tmp_dir.glob("*.part")), [])
            self.assertGreaterEqual(len(closed), 3)

    def test_late_staging_commit_cleans_up_part_and_preserves_existing_artifacts(self) -> None:
        clock = VirtualClock()
        deadline = clock() + 1.0
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            existing = tmp_dir / "existing.png"
            existing.write_bytes(b"original-bytes")
            with self.assertRaises(FileExistsError):
                atomic_write_verified_bytes(existing, b"new-bytes", deadline=deadline, clock=clock, overwrite=False)
            self.assertEqual(existing.read_bytes(), b"original-bytes")

            # Advance past deadline right before atomic_write_verified_bytes checks commit deadline
            clock.advance(1.5)
            fresh = tmp_dir / "late.mp4"
            with self.assertRaises(TimeoutError):
                atomic_write_verified_bytes(fresh, b"video-data", deadline=deadline, clock=clock, overwrite=False)
            self.assertFalse(fresh.exists())
            self.assertEqual(list(tmp_dir.glob("*.part")), [])

            # Symlink target must be rejected
            symlink_target = tmp_dir / "link.mp4"
            symlink_target.symlink_to(existing)
            with self.assertRaises(RuntimeError):
                atomic_write_verified_bytes(symlink_target, b"video-data", deadline=clock() + 5.0, clock=clock, overwrite=True)
            self.assertEqual(existing.read_bytes(), b"original-bytes")

    def test_background_long_decode_slow_poll_bounded(self) -> None:
        clock = VirtualClock()
        polls = [
            ("in_progress", 2.0, ""),
            ("completed", 4.0, "svg-code"),  # 2s create + 3s sleep + 4s get = 9s > 8s budget!
        ]
        idx = 0

        def factory(timeout_ms: int) -> Any:
            def _create(**_kw: Any) -> Any:
                clock.advance(2.0)
                return SimpleNamespace(id="v1_bg_1", status="in_progress", steps=[], output_text="")

            def _get(*, id: str) -> Any:
                nonlocal idx
                st, lat, txt = polls[idx]
                idx += 1
                if lat * 1000.0 > timeout_ms:
                    clock.advance(timeout_ms / 1000.0)
                    raise TimeoutError("Stubbed background poll timeout")
                clock.advance(lat)
                return SimpleNamespace(id=id, status=st, steps=[], output_text=txt)

            return SimpleNamespace(
                interactions=SimpleNamespace(create=_create, get=_get),
                close=lambda: None,
            )

        with tempfile.TemporaryDirectory() as tmp:
            out_svg = Path(tmp) / "scene.svg"
            with self.assertRaises(TimeoutError):
                poll_background_interaction_bounded(
                    create_kwargs={"model": "gemini-4-argon", "input": "svg"},
                    output_path=out_svg,
                    total_budget_s=8.0,
                    poll_interval_s=3.0,
                    client_factory=factory,
                    clock=clock,
                    sleep_fn=clock.sleep,
                )
            self.assertFalse(out_svg.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
