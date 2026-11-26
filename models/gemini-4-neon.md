# Gemini 4 Neon

Google's high-velocity Gemini 4 frontier intelligence model (`gemini-4-neon`), sitting between Gemini 4 Hydrogen (`gemini-4-hydrogen`) and Gemini 4 Argon / Carbon (`gemini-4-argon` / `gemini-4-carbon`). Built for frontier-level quality with fast end-to-end task completion across complex software engineering, UI/UX architecture, interactive code visuals (SVG, Three.js, Canvas, GLSL shaders), and dense multimodal storyboarding. Features a unified 1,048,576-token context window, long decode up to 1M tokens, and four tunable thinking levels (`low`, `medium`, `high` default, `xhigh`).

In `/generate` and `/ui`, reach for `gemini-4-neon` when you want frontier-level creative/architectural reasoning and multi-shot storyboard or complex interactive 3D/SVG generation with faster end-to-end turnaround than deep reasoning passes.

| Field | Value |
|---|---|
| Model ID | `gemini-4-neon` |
| Provider | Gemini API (Google AI Studio key) |
| API | Interactions API — `client.interactions.create` |
| Method | Sync up to 64K tokens (`65,536` default); async `background=True` for long decode up to 1M tokens |
| Type | Frontier Multimodal Reasoning / Storyboarding / Code Visuals (Text output) |
| API key | `GEMINI_API_KEY` env var |
| Docs | https://ai.google.dev/gemini-api/docs/models/gemini-4-neon |
| Cost | Paid tier only (no free tier): $3.00 / 1M input tokens and $15.00 / 1M output + thinking tokens; implicit caching enabled by default — quote current pricing from https://ai.google.dev/gemini-api/docs/pricing and get approval before every call (see SKILL.md, Rules) |

## Request (Python, `google-genai >= 3.2.0` SDK)

### Interactive Code Visuals (SVG / Three.js / Shaders) or Storyboard Planning (sync)
```python
from google import genai
import base64
import mimetypes
from pathlib import Path

client = genai.Client()  # reads GEMINI_API_KEY from env (v1 Interactions API by default)

input_parts = [{"type": "text", "text": prompt}]
for ref_path in ref_paths:
    raw = Path(ref_path).read_bytes()
    if raw.startswith(b"\x89PNG\r\n\x1a\n"):
        mime_type = "image/png"
    elif raw.startswith(b"\xff\xd8\xff"):
        mime_type = "image/jpeg"
    elif raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
        mime_type = "image/webp"
    else:
        mime_type, _ = mimetypes.guess_type(str(ref_path))
    if mime_type not in {"image/png", "image/jpeg", "image/webp", "image/heic", "image/heif"}:
        raise ValueError(f"Unsupported reference MIME {mime_type} for {ref_path}")
    input_parts.append({
        "type": "image",
        "data": base64.b64encode(raw).decode("utf-8"),
        "mime_type": mime_type,
    })

interaction = client.interactions.create(
    model="gemini-4-neon",
    input=input_parts,
    generation_config={
        "thinking_level": "high",  # "low" | "medium" | "high" (default) | "xhigh" — never "minimal"
    },
)
```

### Long decode (>64K tokens, up to 1M tokens via `background=True`)
When generating exhaustive design systems, multi-scene storyboards, or complex interactive 3D/WebGL applications that exceed 65,536 tokens, run under an end-to-end monotonic `deadline` bounding `interactions.create`, sleeps, every `interactions.get` (`types.HttpOptions(timeout=remaining_ms)`), and atomic output commit:
```python
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
import math
import time
from google import genai
from google.genai import types

def call_bounded(fn, deadline: float):
    remaining_s = deadline - time.monotonic()
    if remaining_s <= 0:
        raise TimeoutError("End-to-end deadline exceeded before SDK call.")
    timeout_ms = max(1, math.ceil(remaining_s * 1000))
    scoped = genai.Client(http_options=types.HttpOptions(timeout=timeout_ms))
    close_fn = getattr(scoped, "close", None)
    pool = ThreadPoolExecutor(max_workers=1)
    fut = pool.submit(fn, scoped)
    try:
        res = fut.result(timeout=timeout_ms / 1000.0)
    except FuturesTimeoutError as exc:
        fut.cancel()
        if callable(close_fn):
            close_fn()
        raise TimeoutError(f"SDK call exceeded remaining {remaining_s:.2f}s deadline.") from exc
    finally:
        pool.shutdown(wait=False, cancel_futures=True)
    if callable(close_fn):
        close_fn()
    if time.monotonic() > deadline:
        raise TimeoutError("SDK call finished after end-to-end deadline expired.")
    return res

deadline = time.monotonic() + 900.0  # 15-minute end-to-end budget across create + polling + commit
interaction = call_bounded(
    lambda c: c.interactions.create(
        model="gemini-4-neon",
        input=prompt,
        background=True,
        generation_config={"max_output_tokens": 131072, "thinking_level": "high"},
    ),
    deadline,
)

while interaction.status in ("in_progress", "queued"):
    remaining_s = deadline - time.monotonic()
    if remaining_s <= 0:
        raise TimeoutError(f"Long decode timed out (interaction={interaction.id}); check status before rerunning.")
    time.sleep(min(5.0, remaining_s))
    interaction = call_bounded(lambda c: c.interactions.get(id=interaction.id), deadline)

if interaction.status != "completed":
    raise RuntimeError(f"Long decode ended with status={interaction.status!r} (interaction={interaction.id})")

full_text = "".join(
    content.text
    for step in (interaction.steps or [])
    if step.type == "model_output"
    for content in (step.content or [])
    if content.type == "text"
)
```

## Response handling

```python
from pathlib import Path

output_text = interaction.output_text
if not output_text:
    raise RuntimeError(f"Empty response (status={interaction.status})")

Path(output_path).write_text(output_text, encoding="utf-8")
assert Path(output_path).stat().st_size > 0
```

Verify the saved artifact (`.svg`, `.html`, or storyboard `.md`) exists and is non-empty on disk before writing the matching `.json` sidecar. Log `interaction.id` in `response_id` so follow-up turns can chain statefully via `previous_interaction_id`.

## Notes

- **Valid `thinking_level` values are `"low"`, `"medium"`, `"high"` (default), and `"xhigh"` only.** Passing `"minimal"` or a legacy `thinking_budget` raises a validation error on `gemini-4-neon`. Reserve `"xhigh"` for hard multi-step engineering or shader/geometry math where `"high"` falls short.
- **Do not pass sampling parameters (`temperature`, `top_p`, `top_k`).** They are deprecated and rejected/ignored across the Gemini 4 family.
- **`max_output_tokens` covers both thinking and final output** within the shared 1,048,576-token window. Leave it unset (defaults to `65,536`) or set at least `32,768`.
- **Paid tier only:** Every token processed (including thinking tokens) is billed at $3.00 / 1M input and $15.00 / 1M output. Always quote and get explicit user approval before calling `gemini-4-neon`.
