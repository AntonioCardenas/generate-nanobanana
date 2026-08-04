# Gemini Omni Flash

Google's cost-efficient video model — up to 10 seconds of 720p video with synchronized audio per clip, and it can take image or video (not just text) as input for conversational editing. This is the video default; there's no separate "quality" video tier wired into this skill yet — if a job needs 1080p/4K or longer clips, that's Veo territory and out of scope until a `veo.md` recipe is added.

| Field | Value |
|---|---|
| Model ID | `gemini-omni-flash-preview` |
| Provider | Gemini API (Google AI Studio key) |
| API | Interactions API — `client.interactions.create` |
| Method | Sync for small clips (inline base64); large outputs use submit-then-poll via the Files API (`delivery: "uri"`) |
| Type | Video |
| API key | `GEMINI_API_KEY` env var |
| Docs | https://ai.google.dev/gemini-api/docs/omni |
| Cost | Quote per-second pricing from https://ai.google.dev/gemini-api/docs/pricing before running — this is the model the cost-approval gate exists for, alongside image generation (see SKILL.md, Rules) |

## Request (Python, `google-genai` SDK)

### Text-to-video
```python
import base64
from google import genai

client = genai.Client()

interaction = client.interactions.create(
    model="gemini-omni-flash-preview",
    input=prompt,
)
with open(output_path, "wb") as f:
    f.write(base64.b64decode(interaction.output_video.data))
```

### Image-to-video / reference-guided
Pass reference images (start frame, subject, style) as `image` input parts alongside the text instruction — don't re-describe a still in words when the pixels exist:
```python
import base64
from google import genai

client = genai.Client()

with open(image_path, "rb") as f:
    frame_bytes = f.read()

interaction = client.interactions.create(
    model="gemini-omni-flash-preview",
    input=[
        {"type": "image", "data": base64.b64encode(frame_bytes).decode("utf-8"), "mime_type": "image/png"},
        {"type": "text", "text": prompt},
    ],
)
with open(output_path, "wb") as f:
    f.write(base64.b64decode(interaction.output_video.data))
```

### Stateful editing
Chain an edit onto a prior generation instead of re-describing the whole scene:
```python
edited = client.interactions.create(
    model="gemini-omni-flash-preview",
    previous_interaction_id=interaction.id,
    input="Make the violin invisible.",
)
```

### Large outputs — retrieve via URI instead of inline base64
```python
import time
from google import genai

client = genai.Client()

interaction = client.interactions.create(
    model="gemini-omni-flash-preview",
    input=prompt,
    response_format={"type": "video", "delivery": "uri"},
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

The inline path returns `output_video.data` as base64 — decode with `base64.b64decode` before writing; don't treat it as raw bytes. The URI path returns `output_video.uri`, which stays pending until the corresponding `files.get` state reaches `ACTIVE` (check `FAILED` too, so a broken job doesn't spin forever). Download and save immediately — generated-video URIs are not guaranteed to stay valid indefinitely. The response also carries an `id` — log it so a later edit can chain onto this one via `previous_interaction_id`.

## Notes

- This is a preview model name and the API surface for it may still be settling — before relying on this recipe for a real (paid) run, do a quick check against the current docs, since Google iterates on this one faster than the GA image models.
- Because this is billed per second, this is exactly the model the skill's "quote cost, wait for approval" rule exists for — alongside image generation, which is also billable. Never fire this off speculatively.
- To keep a clip visually on-model with approved stills, pass the approved image as an `image` input part rather than re-describing the scene in text — the still anchors palette, character, and framing; a text-only prompt re-rolls the look.
- No `seed` or reproducibility parameter is documented on the Interactions API for this model. `previous_interaction_id` (stateful editing, above) is the real coherence lever for video — not a seed — so log the response `id` in every sidecar.
