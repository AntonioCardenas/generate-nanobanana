# Nano Banana 2 Lite

Fastest, cheapest Gemini image model. Default for drafts and iteration — not optimized for multiple reference inputs or multi-turn sequential editing, so switch to Nano Banana Pro if a job needs more than 1-2 references or careful multi-step edits.

| Field | Value |
|---|---|
| Model ID | `gemini-3.1-flash-lite-image` |
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
for ref_path in reference_images:  # 0-2 images, keep it light on this model
    with open(ref_path, "rb") as f:
        input_parts.append({
            "type": "image",
            "data": base64.b64encode(f.read()).decode("utf-8"),
            "mime_type": "image/png",
        })

interaction = client.interactions.create(
    model="gemini-3.1-flash-lite-image",
    input=input_parts,
    response_format={
        "type": "image",
        "image_size": "1K",       # 512px | 1K | 2K | 4K
        "aspect_ratio": "16:9",   # 1:1, 16:9, 9:16, 4:3, 3:4, 21:9, etc.
    },
)
```

## Response handling

```python
from pathlib import Path
import base64

if interaction.output_image is None or interaction.output_image.data is None:
    # No image came back — only text (a refusal, safety block, or commentary).
    # Surface that text to the user and stop. No file, no sidecar.
    raise RuntimeError(interaction.output_text or "empty response")

Path(output_path).write_bytes(base64.b64decode(interaction.output_image.data))
assert Path(output_path).stat().st_size > 0
```

Two rules that are not optional:

- **`output_image.data` is base64-encoded text, not raw bytes** — decode it with `base64.b64decode` before writing. Writing the string directly (or double-decoding) is the classic way a generation "succeeds" but no valid image ever lands on disk.
- **Verify the image file exists and is non-empty before writing the sidecar.** The sidecar is the record that an image exists — a sidecar without its image is a false log entry.

`output_text`, when present, is the model's commentary — safe to relay to the user, never the file.

## Notes

- No `seed` or reproducibility parameter is documented for this model on the Interactions API — treat every call as non-deterministic. For "same image but change X," reuse the exact prompt and references from the sidecar and change only the delta (see SKILL.md, Determinism & coherence).
- Log the response `id` in the sidecar — it's what lets a later call chain onto this one via `previous_interaction_id` if that's supported for image edits; re-verify against current docs before relying on it.
- A picked draft's identity does not transfer to Nano Banana 2 or Pro. When promoting a picked draft, pass the draft image itself as a reference in the final call (see SKILL.md, Determinism & coherence).
- Rate limits are generous on this tier but still real — one request at a time per the skill's Rules section, not parallel batches.
- If a request needs on-image text (signage, packaging, readable UI copy), this model is weaker at it than Nano Banana 2 or Pro — flag that to the user rather than silently producing garbled text.
