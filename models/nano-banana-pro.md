# Nano Banana Pro

Google's highest-quality image model. Strong at composition with multiple references (up to 14 input images), consistent characters across a scene (up to 5 people), and legible on-image text — infographics, posters, product mockups. Reach for this once a draft on Nano Banana 2 Lite has been picked, not before; it costs roughly 2-3x the Lite tier.

| Field | Value |
|---|---|
| Model ID | `gemini-3-pro-image` |
| Provider | Gemini API (Google AI Studio key) |
| API | Interactions API — `client.interactions.create` |
| Method | Sync — one call, one reply |
| Type | Image |
| API key | `GEMINI_API_KEY` env var |
| Docs | https://ai.google.dev/gemini-api/docs/image-generation |
| Cost | Billable per call — quote current pricing from https://ai.google.dev/gemini-api/docs/pricing and get approval before every call, not just video (see SKILL.md, Rules) |

`gemini-3-pro-image-preview` was deprecated 2026-05-28 and shut down 2026-06-25. `gemini-3-pro-image` is the current GA replacement — re-check the docs link above before relying on this ID, since Google rotates preview/GA names on its own schedule.

## Request (Python, `google-genai` SDK)

```python
from google import genai
import base64

client = genai.Client()

input_parts = [{"type": "text", "text": prompt}]
for ref_path in reference_images:  # up to 14 supported here
    with open(ref_path, "rb") as f:
        input_parts.append({
            "type": "image",
            "data": base64.b64encode(f.read()).decode("utf-8"),
            "mime_type": "image/png",
        })

interaction = client.interactions.create(
    model="gemini-3-pro-image",
    input=input_parts,
    response_format={
        "type": "image",
        "image_size": "2K",       # 1K | 2K | 4K
        "aspect_ratio": "16:9",
    },
)
```

## Response handling

Same shape as Nano Banana 2 Lite — see that recipe for the full save snippet. Decode `output_image.data` with `base64.b64decode` and write it to disk, verify the file exists and is non-empty **before** writing the sidecar. A text-only response means the generation failed: surface the text, save nothing, log nothing.

## Notes

- Model IDs on this tier move — Google shut down `gemini-3-pro-image-preview` in favor of the GA `gemini-3-pro-image` on 2026-06-25. If a call 404s, check https://ai.google.dev/gemini-api/docs/image-generation for the current ID and update this file.
- Worth the extra cost specifically for: text-heavy compositions, multi-image fusion, character consistency across a series. For a simple single-subject image, Lite is usually good enough — don't upgrade by default.
- This is the series tier. For images that must match each other (a character across scenes, a product line, episode covers), pass the approved first image of the series as one of the references in every subsequent call — refs anchor consistency far harder than a repeated description does.
- No `seed` or reproducibility parameter is documented for this model on the Interactions API. Hold `image_size` and `aspect_ratio` fixed across reruns for a similar look — changing either re-rolls the composition — and log the response `id` for potential stateful chaining (see SKILL.md, Determinism & coherence).
