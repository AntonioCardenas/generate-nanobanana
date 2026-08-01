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
from google import genai
from google.genai import types

client = genai.Client()  # reads GEMINI_API_KEY from env

parts = []
for ref_path in reference_images:  # 0-2 images, keep it light on this model
    parts.append(types.Part.from_bytes(
        data=open(ref_path, "rb").read(),
        mime_type="image/png",
    ))
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

```python
from pathlib import Path

parts = response.candidates[0].content.parts
image_part = next((p for p in parts if p.inline_data is not None), None)

if image_part is None:
    # No image came back — only text (a refusal, safety block, or commentary).
    # Surface that text to the user and stop. No file, no sidecar.
    raise RuntimeError(" ".join(p.text for p in parts if p.text) or "empty response")

Path(output_path).write_bytes(image_part.inline_data.data)
assert Path(output_path).stat().st_size > 0
```

Two rules that are not optional:

- **`inline_data.data` is already raw bytes** — the `google-genai` SDK un-base64s it for you. Base64-decoding it again writes a corrupt file or crashes mid-save; this is the classic way a generation "succeeds" but no image ever lands on disk. Write the bytes as-is, with the extension matching `inline_data.mime_type`.
- **Verify the image file exists and is non-empty before writing the sidecar.** The sidecar is the record that an image exists — a sidecar without its image is a false log entry.

`text` parts are the model's commentary — safe to relay to the user, never the file. `response.usage_metadata` carries token counts if you want exact cost per generation rather than the ballpark above.

## Notes

- Seed repeatability is best-effort: same seed + same prompt + same refs + same config lands very close to the same image, not guaranteed pixel-identical. Changing `image_size` or `aspect_ratio` re-rolls the composition regardless of seed — hold those fixed when iterating on a draft the user liked.
- A seed picked here does not transfer to Nano Banana 2 or Pro. When promoting a picked draft, pass the draft image itself as a reference in the final call (see SKILL.md, Determinism & coherence).
- Rate limits are generous on this tier but still real — one request at a time per the skill's Rules section, not parallel batches.
- If a request needs on-image text (signage, packaging, readable UI copy), this model is weaker at it than Nano Banana 2 or Pro — flag that to the user rather than silently producing garbled text.
