# Nano Banana Pro

Google's highest-quality image model. Strong at composition with multiple references (up to 14 input images), consistent characters across a scene (up to 5 people), and legible on-image text — infographics, posters, product mockups. Reach for this once a draft on Nano Banana 2 Lite has been picked, not before; it costs roughly 2-3x the Lite tier.

| Field | Value |
|---|---|
| Model ID | `gemini-3-pro-image-preview` |
| Provider | Gemini API (Google AI Studio key) |
| Method | Sync — one call, one reply |
| Type | Image |
| API key | `GEMINI_API_KEY` env var |
| Docs | https://ai.google.dev/gemini-api/docs/image-generation |
| Cost | ~$0.13-0.30 per 1K-4K image depending on resolution |

## Request (Python, `google-genai` SDK)

```python
from pathlib import Path

from google import genai
from google.genai import types

client = genai.Client()

REFS_ROOT = (Path.home() / "generations" / "refs").resolve()
ALLOWED_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}
MAX_REF_BYTES = 20 * 1024 * 1024  # every reference is uploaded to the API — cap it

parts = []
for ref_path in reference_images:  # up to 14 supported here
    raw = Path(ref_path)
    # Absolute paths only come from a linked set the user registered (see SKILL.md rules);
    # relative paths must stay inside the refs library — no ".." tricks, no symlinks out.
    p = raw.resolve() if raw.is_absolute() else (REFS_ROOT / raw).resolve()
    if not raw.is_absolute() and not p.is_relative_to(REFS_ROOT):
        raise ValueError(f"reference escapes {REFS_ROOT}: {ref_path}")
    mime = ALLOWED_TYPES.get(p.suffix.lower())
    if mime is None or not p.is_file():
        raise ValueError(f"not an allowed reference image: {ref_path}")
    if p.stat().st_size > MAX_REF_BYTES:
        raise ValueError(f"reference too large: {ref_path}")
    parts.append(types.Part.from_bytes(data=p.read_bytes(), mime_type=mime))
parts.append(types.Part.from_text(prompt))

response = client.models.generate_content(
    model="gemini-3-pro-image-preview",
    contents=[{"role": "user", "parts": parts}],
    config=types.GenerateContentConfig(
        response_modalities=["IMAGE", "TEXT"],
        seed=seed,                 # always set one — random int if the user doesn't care — and log it in the sidecar
        image_config=types.ImageConfig(
            image_size="2K",       # 1K | 2K | 4K
            aspect_ratio="16:9",
        ),
    ),
)
```

## Response handling

Same shape as Nano Banana 2 Lite: iterate `response.candidates[0].content.parts`, decode `inline_data` to a file, use `response.usage_metadata` for exact cost if needed.

## Notes

- This is a preview model — the ID can change when Google promotes it to stable. If a call 404s, check https://ai.google.dev/gemini-api/docs/image-generation for the current ID and update this file.
- Worth the extra cost specifically for: text-heavy compositions, multi-image fusion, character consistency across a series. For a simple single-subject image, Lite is usually good enough — don't upgrade by default.
- This is the series tier. For images that must match each other (a character across scenes, a product line, episode covers), pass the approved first image of the series as one of the references in every subsequent call — refs anchor consistency far harder than a repeated description does.
- Seed repeatability is best-effort: same seed + prompt + refs + config lands very close, not guaranteed pixel-identical. Hold `image_size` and `aspect_ratio` fixed across reruns — changing either re-rolls the composition regardless of seed.
