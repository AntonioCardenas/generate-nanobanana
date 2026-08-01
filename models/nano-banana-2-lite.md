# Nano Banana 2 Lite

Fastest, cheapest Gemini image model. Default for drafts and iteration — not optimized for multiple reference inputs or multi-turn sequential editing, so switch to Nano Banana Pro if a job needs more than 1-2 references or careful multi-step edits.

| Field | Value |
|---|---|
| Model ID | `gemini-3.1-flash-lite-image` |
| Provider | Gemini API (Google AI Studio key) |
| Method | Sync — one call, one reply |
| Type | Image |
| API key | `GEMINI_API_KEY` env var |
| Docs | https://ai.google.dev/gemini-api/docs/image-generation |
| Cost | ~$0.03-0.05 per 1K image, roughly half that of Nano Banana 2 standard |

## Request (Python, `google-genai` SDK)

```python
from pathlib import Path

from google import genai
from google.genai import types

client = genai.Client()  # reads GEMINI_API_KEY from env

REFS_ROOT = (Path.home() / "generations" / "refs").resolve()
ALLOWED_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}
MAX_REF_BYTES = 20 * 1024 * 1024  # every reference is uploaded to the API — cap it

parts = []
for ref_path in reference_images:  # 0-2 images, keep it light on this model
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
    model="gemini-3.1-flash-lite-image",
    contents=[{"role": "user", "parts": parts}],
    config=types.GenerateContentConfig(
        response_modalities=["IMAGE", "TEXT"],
        seed=seed,                 # always set one — random int if the user doesn't care — and log it in the sidecar
        image_config=types.ImageConfig(
            image_size="1K",       # 512 | 1K | 2K | 4K
            aspect_ratio="16:9",   # 1:1, 16:9, 9:16, 4:3, 3:4, 21:9, etc.
        ),
    ),
)
```

## Response handling

Walk `response.candidates[0].content.parts`. Each part is either `inline_data` (the image — base64 bytes, decode and write to disk with the mime type's extension) or `text` (the model's commentary — safe to log but not the file). `response.usage_metadata` carries token counts if you want to compute exact cost per generation rather than using the ballpark above.

## Notes

- Seed repeatability is best-effort: same seed + same prompt + same refs + same config lands very close to the same image, not guaranteed pixel-identical. Changing `image_size` or `aspect_ratio` re-rolls the composition regardless of seed — hold those fixed when iterating on a draft the user liked.
- A seed picked here does not transfer to Nano Banana 2 or Pro. When promoting a picked draft, pass the draft image itself as a reference in the final call (see SKILL.md, Determinism & coherence).
- Rate limits are generous on this tier but still real — one request at a time per the skill's Rules section, not parallel batches.
- If a request needs on-image text (signage, packaging, readable UI copy), this model is weaker at it than Nano Banana 2 or Pro — flag that to the user rather than silently producing garbled text.
