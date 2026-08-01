# Nano Banana 2

Google's generalist image model — the middle tier between Lite and Pro. Noticeably better than Lite at on-image text, world knowledge, and detail, at roughly twice Lite's price and still well under Pro. This is the default for the version that ships when the job doesn't need Pro's heavy multi-image fusion or character-consistency work.

| Field | Value |
|---|---|
| Model ID | `gemini-3.1-flash-image` |
| Provider | Gemini API (Google AI Studio key) |
| Method | Sync — one call, one reply |
| Type | Image |
| API key | `GEMINI_API_KEY` env var |
| Docs | https://ai.google.dev/gemini-api/docs/models/gemini-3.1-flash-image |
| Cost | ~$0.05 (512px) / $0.07 (1K) / $0.10 (2K) / $0.15 (4K) per image |

## Request (Python, `google-genai` SDK)

```python
from google import genai
from google.genai import types

client = genai.Client()  # reads GEMINI_API_KEY from env

parts = []
for ref_path in reference_images:  # keep it to a handful here
    parts.append(types.Part.from_bytes(
        data=open(ref_path, "rb").read(),
        mime_type="image/png",
    ))
parts.append(types.Part.from_text(prompt))

response = client.models.generate_content(
    model="gemini-3.1-flash-image",
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

Same shape as the other image models: walk `response.candidates[0].content.parts`, decode `inline_data` to a file, log any `text` parts as commentary. `response.usage_metadata` carries token counts — image output is billed per token ($60/1M as of mid-2026), so this gives exact cost when the ballpark isn't enough.

## Notes

- Don't draft here — Lite is still the iteration tier. Come to this model with a picked draft, or when a single-pass job needs readable on-image text that Lite garbles.
- A Lite draft's seed means nothing to this model — the coherence lever when promoting a draft is the draft itself: pass the picked image as a reference alongside the original prompt, so the final is anchored to approved pixels instead of a fresh roll of the same words.
- Seed repeatability is best-effort: same seed + prompt + refs + config lands very close, not guaranteed pixel-identical. Hold `image_size` and `aspect_ratio` fixed across reruns — changing either re-rolls the composition regardless of seed.
- Keep reference images to a handful. Large multi-image fusion (up to 14 refs) and consistent characters across a series are what Nano Banana Pro is for — don't force them through this model.
- Pricing above is from https://ai.google.dev/gemini-api/docs/pricing — check it before quoting, these numbers move.
