# Gemini Omni Flash

Google's cost-efficient video model — up to 10 seconds of 720p video with synchronized audio per clip, and it can take image or video (not just text) as input for conversational editing. This is the video default; there's no separate "quality" video tier wired into this skill yet — if a job needs 1080p/4K or longer clips, that's Veo territory and out of scope until a `veo.md` recipe is added.

| Field | Value |
|---|---|
| Model ID | `gemini-omni-flash-preview` |
| Provider | Gemini API (Google AI Studio key) |
| Method | **Async** — submit, then poll |
| Type | Video |
| API key | `GEMINI_API_KEY` env var |
| Docs | https://ai.google.dev/gemini-api/docs/video (check for the Omni Flash section specifically, it's a newer addition) |
| Cost | Quote per-second pricing from the docs before running — this is the model the cost-approval gate exists for |

## Request (Python, `google-genai` SDK)

Video generation on Gemini follows the same long-running-operation pattern as Veo: submit the job, then poll until done.

```python
import time
from google import genai
from google.genai import types

client = genai.Client()

operation = client.models.generate_videos(
    model="gemini-omni-flash-preview",
    prompt=prompt,
    image=types.Image.from_file(image_path) if image_path else None,
    config=types.GenerateVideosConfig(
        number_of_videos=1,
        duration_seconds=10,   # max 10s on this model
        generate_audio=True,
        seed=seed,             # optional — pass the user's pinned/chosen seed if they have one; omit otherwise
    ),
)

# Poll every 10-15s — don't hammer this faster, jobs typically take 1-3 minutes
while not operation.done:
    time.sleep(10)
    operation = client.operations.get(operation)

video = operation.response.generated_videos[0]
video.video.save(output_path)  # or write video.video.video_bytes to disk manually
```

## Response handling

`operation.done` flips to `True` when the job finishes. On success, `operation.response.generated_videos` holds the clip(s); on failure, check `operation.error` before assuming it hung. Download and save immediately — generated-video URLs are not guaranteed to stay valid indefinitely.

## Notes

- This is a preview model name and the API surface for it may still be settling — before relying on this recipe for a real (paid) run, do a quick check against the current docs, since Google shipped this to the developer API only recently.
- Because this is async and billed per second, this is exactly the model the skill's "quote cost, wait for approval" rule is guarding. Never fire this off speculatively.
- To keep a clip visually on-model with approved stills, pass the approved image as the `image=` input rather than re-describing the scene in text — the still anchors palette, character, and framing; a text-only prompt re-rolls the look.
- Seed on video is the weakest of the coherence levers — best-effort like on the image models, and this preview API surface is still settling, so confirm the current docs accept it before a paid run and drop it if the call rejects it. The still-image input is what actually holds the look. When a seed was passed, log it in the sidecar's `params` like any image run.
