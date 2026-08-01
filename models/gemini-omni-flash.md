# Gemini Omni Flash

Google's cost-efficient video model — up to 10 seconds of 720p video at 24 fps with synchronized audio per clip, and it can take image or video (not just text) as input for conversational editing. This is the video default; there's no separate "quality" video tier wired into this skill yet — if a job needs 1080p/4K or longer clips, that's Veo territory and out of scope until a `veo.md` recipe is added.

| Field | Value |
|---|---|
| Model ID | `gemini-omni-flash-preview` |
| Provider | Gemini API (Google AI Studio key) |
| Method | **Interactions API** — one blocking call, typically 30-90s; poll only if it returns still running |
| Type | Video, with native synchronized audio (no flag to pass) |
| API key | `GEMINI_API_KEY` env var |
| Docs | https://ai.google.dev/gemini-api/docs/omni |
| Cost | $0.10 per second of output video ($0.30-$1.00 for 3-10s clips), from the pricing docs as of 2026-08-01 — re-quote before every paid run |

## Request (Python, `google-genai` SDK)

Omni Flash runs on the Interactions API, not the Veo-style `generate_videos` long-running operation (see Notes for what happens if you try that). One call does the whole job:

```python
import base64
import time

import google.genai as genai

client = genai.Client()  # reads GEMINI_API_KEY from env

interaction = client.interactions.create(
    model="gemini-omni-flash-preview",
    input=prompt,     # to animate a still, pass a list mixing text and an image part — see docs
    timeout=600.0,    # generation happens inside this call; give it room
)

# The call usually returns already completed. Poll only if it comes back still running.
deadline = time.monotonic() + 600
while getattr(interaction, "status", None) in ("queued", "in_progress"):
    if time.monotonic() > deadline:
        raise TimeoutError(f"video generation timed out; interaction id: {interaction.id}")
    time.sleep(10)
    interaction = client.interactions.get(interaction.id)

if getattr(interaction, "output_video", None) is None or not interaction.output_video.data:
    raise RuntimeError(
        f"no video in response; status={getattr(interaction, 'status', None)!r} — "
        "inspect the interaction before assuming it hung"
    )

with open(output_path, "wb") as f:
    f.write(base64.b64decode(interaction.output_video.data))
```

## Response handling

`interaction.output_video.data` holds the clip base64-encoded for responses under 4MB — a real 10s 720p clip came back at ~2.7MB, so text-to-video jobs normally fit inline. For anything larger, pass `delivery="uri"` on the create call, then poll `client.files.get()` until the file state is `ACTIVE` and download it with `client.files.download()`, per the docs. Save immediately either way; don't assume a delivery URI stays valid.

## Notes

- **Do not use `client.models.generate_videos` for this model.** Verified against the live API on 2026-08-01, that path fails three independent ways before producing a frame: the server rejects the model for that RPC ("`models/gemini-omni-flash-preview` … is not supported for predictLongRunning", 404), the SDK has deprecated the `prompt=`/`image=` argument style it needs, and `generate_audio=True` raises client-side in Developer API mode ("only supported in Gemini Enterprise Agent Platform mode"). Audio needs no flag on the Interactions path — it's native to the model, and the produced mp4 carries a real audio track.
- Because this is billed per second, this is exactly the model the skill's "quote cost, wait for approval" rule is guarding. Never fire this off speculatively.
- To keep a clip visually on-model with approved stills, pass the approved image as an input part rather than re-describing the scene in text — the still anchors palette, character, and framing; a text-only prompt re-rolls the look.
- Seed on video is the weakest of the coherence levers, and the Interactions API surface for it is still settling — confirm the current docs accept it before relying on it in a paid run. The still-image input is what actually holds the look. When a seed was passed, log it in the sidecar's `params` like any image run.
