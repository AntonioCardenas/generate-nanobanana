# Nano Banana 2

Google's generalist image model — the middle tier between Lite and Pro. Noticeably better than Lite at on-image text, world knowledge, and detail, at roughly twice Lite's price and still well under Pro. This is the default for the version that ships when the job doesn't need Pro's heavy multi-image fusion or character-consistency work.

| Field | Value |
|---|---|
| Model ID | `gemini-3.1-flash-image` |
| Provider | Gemini API (Google AI Studio key) |
| API | Interactions API — `client.interactions.create` |
| Method | Sync — one call, one reply |
| Type | Image |
| API key | `GEMINI_API_KEY` env var |
| Docs | https://ai.google.dev/gemini-api/docs/image-generation |
| Cost | Billable per call — quote current pricing from https://ai.google.dev/gemini-api/docs/pricing and get approval before every call, not just video (see SKILL.md, Rules) |

## Request (Python, `google-genai` SDK)

```python
from google import genai
import base64

client = genai.Client()  # reads GEMINI_API_KEY from env

input_parts = [{"type": "text", "text": prompt}]
for ref_path in reference_images:  # keep it to a handful here
    with open(ref_path, "rb") as f:
        input_parts.append({
            "type": "image",
            "data": base64.b64encode(f.read()).decode("utf-8"),
            "mime_type": "image/png",
        })

interaction = client.interactions.create(
    model="gemini-3.1-flash-image",
    input=input_parts,
    response_format={
        "type": "image",
        "image_size": "1K",       # 512px | 1K | 2K | 4K
        "aspect_ratio": "16:9",   # 1:1, 16:9, 9:16, 4:3, 3:4, 21:9, etc.
    },
)
```

## Response handling

Same shape as Nano Banana 2 Lite — see that recipe for the full save snippet. The short version: decode `output_image.data` with `base64.b64decode` and write it to disk, and verify the file exists and is non-empty **before** writing the sidecar. If `output_image` is empty and only `output_text` came back, the generation failed — surface that text to the user, save nothing, log nothing.

## Notes

- Don't draft here — Lite is still the iteration tier. Come to this model with a picked draft, or when a single-pass job needs readable on-image text that Lite garbles.
- No `seed` or reproducibility parameter is documented for this model on the Interactions API — a Lite draft's identity doesn't carry forward either way. The coherence lever when promoting a draft is the draft itself: pass the picked image as a reference alongside the original prompt, so the final is anchored to approved pixels instead of a fresh roll of the same words.
- Log the response `id` in the sidecar for potential stateful chaining (see SKILL.md, Determinism & coherence).
- Keep reference images to a handful. Large multi-image fusion (up to 14 refs) and consistent characters across a series are what Nano Banana Pro is for — don't force them through this model.
- Pricing moves — check https://ai.google.dev/gemini-api/docs/pricing before quoting rather than trusting any number cached from a previous session.
