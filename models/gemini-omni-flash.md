# Gemini Omni Flash

Google's GA multimodal video generation and conversational editing model (`gemini-omni-1.1-flash`). Generates 3–10 second clips at 24 FPS with synchronized audio across `360p`, `720p` (default), `1080p` (upscaled), and `4k` (upscaled), and supports image-to-video, first/last frame interpolation, scene extension, and multi-turn conversational editing.

| Field | Value |
|---|---|
| Model ID | `gemini-omni-1.1-flash` |
| Provider | Gemini API (Google AI Studio key) |
| API | Interactions API — `client.interactions.create` |
| Method | Sync for standard clips (inline base64); large outputs (>4MB / >720p) use `delivery: "uri"` via the Files API |
| Type | Video |
| API key | `GEMINI_API_KEY` env var |
| Docs | https://ai.google.dev/gemini-api/docs/omni |
| Cost | ~$0.10 / second at 720p ($17.50 / 1M video output tokens at ~5,792 tokens/s; $1.50 / 1M input tokens; $9.00 / 1M text output tokens) — quote current pricing from https://ai.google.dev/gemini-api/docs/pricing and get approval before running (see SKILL.md, Rules) |

`gemini-omni-flash-preview` and the Gemini API `veo-3.1-*-preview` endpoints were shut down on 2026-10-22 (`veo-3.0-*` shut down 2026-06-30). `gemini-omni-1.1-flash` is the GA replacement for all of them.

## Request (Python, `google-genai` SDK)

### Text-to-video (with aspect ratio & resolution control)
```python
import base64
from google import genai

client = genai.Client()

interaction = client.interactions.create(
    model="gemini-omni-1.1-flash",
    input=prompt,
    response_format={
        "type": "video",
        "aspect_ratio": "16:9",  # "16:9" (default) | "9:16"
        "resolution": "720p",    # "360p" | "720p" (default) | "1080p" (upscaled) | "4k" (upscaled)
    },
)
with open(output_path, "wb") as f:
    f.write(base64.b64decode(interaction.output_video.data))
```

### Image-to-video & first/last frame interpolation
Pass 1 image as a starting frame/reference, or 2 images to interpolate smoothly from first frame to last frame. You can also bind roles explicitly in the prompt with `<FIRST_FRAME>`, `<LAST_FRAME>`, `<IMAGE_REF_0>`, and `<VIDEO_REF_0>`:
```python
import base64
from google import genai

client = genai.Client()

with open(image_path, "rb") as f:
    frame_bytes = f.read()

interaction = client.interactions.create(
    model="gemini-omni-1.1-flash",
    input=[
        {"type": "image", "data": base64.b64encode(frame_bytes).decode("utf-8"), "mime_type": "image/png"},
        {"type": "text", "text": prompt},
    ],
)
with open(output_path, "wb") as f:
    f.write(base64.b64decode(interaction.output_video.data))
```

### Stateful editing & multi-turn video extension
Chain an edit or a 3–10 second continuation onto a prior generation without re-uploading the video:
```python
edited = client.interactions.create(
    model="gemini-omni-1.1-flash",
    previous_interaction_id=interaction.id,
    input="Make the violin invisible.",  # or "Continue the scene: the camera pans across the mountains."
)
```

### Extending an uploaded video
```python
video_file = client.files.upload(file="my_video.mp4")  # must be <=10s

extended = client.interactions.create(
    model="gemini-omni-1.1-flash",
    input=[
        {"type": "video", "uri": video_file.uri},
        {"type": "text", "text": "Continue the scene."},
    ],
)
```

### Large outputs (>4MB / 1080p / 4K) — retrieve via URI
```python
import time
from google import genai

client = genai.Client()

interaction = client.interactions.create(
    model="gemini-omni-1.1-flash",
    input=prompt,
    response_format={"type": "video", "resolution": "1080p", "delivery": "uri"},
)

video_output = interaction.output_video
file_name = video_output.uri.split("/")[-1]

while True:
    f_info = client.files.get(name=f"files/{file_name}")
    if f_info.state.name == "ACTIVE":
        break
    if f_info.state.name == "FAILED":
        raise RuntimeError("Generation failed.")
    time.sleep(5)

video_bytes = client.files.download(file=video_output.uri)
with open(output_path, "wb") as f:
    f.write(video_bytes)
```

## Response handling

The inline path returns `output_video.data` as base64 — decode with `base64.b64decode` before writing; don't treat it as raw bytes. For videos larger than 4MB (such as `1080p` or `4k` outputs), use `delivery: "uri"`, poll `client.files.get` until `ACTIVE` (checking `FAILED` too), and download immediately — note that `output_video.uri` is only returned on the initial creation response, whereas a later `GET /v1beta/interactions/{id}` returns inline base64. Always verify the `.mp4` landed on disk and is non-empty before writing the sidecar, and log `interaction.id` in `response_id`.

## Notes

- **Explicit `task` hint (fallback only):** Rely on natural-language prompting first. If the model misinterprets the mode, pass `generation_config={"video_config": {"task": "image_to_video"}}` (allowed: `text_to_video`, `image_to_video`, `reference_to_video`, `edit`, `extend`).
- **Single-shot vs multi-shot default:** By default, Omni Flash crafts a multi-shot narrative. If the user wants one continuous shot, include `"In a single unbroken scene, no scene cuts"` in the prompt.
- **Unsupported parameters:** `temperature`, `top_p`, stop sequences, system instructions, and separate negative-prompt fields are unsupported — weave exclusions into the prompt itself (e.g., `"No dialogue, no extra sound effects"`).
- **Cost & approval gate:** Billed per output token (~$0.10/sec at 720p; ~`$1.01` for a 10-second clip) with no free tier. Quote expected duration, resolution, and cost and wait for explicit approval before every call.
