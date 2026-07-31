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

- Rate limits are generous on this tier but still real — one request at a time per the skill's Rules section, not parallel batches.
- If a request needs on-image text (signage, packaging, readable UI copy), this model is weaker at it than Nano Banana Pro — flag that to the user rather than silently producing garbled text.
