---
name: generate
description: Generate images and videos using Google's Gemini media models (Nano Banana 2 Lite, Nano Banana Pro, Gemini Omni Flash) via the Gemini API. Use this whenever the user asks to generate, create, or make an image or video, wants a thumbnail, wants to animate a still image, or invokes /generate — even if they don't name a specific model, and even if they just describe a visual they want without saying "generate."
---

# /generate

Calls Google's Gemini media models directly through the Gemini API — no third-party routing layer. One key, one bill, and access to the newest Google-specific features (Nano Banana Pro's multi-image fusion, Omni Flash's synced audio) as soon as they ship.

## How a generation flows

1. **Route** — pick the model for the job (draft image, quality image, or video) and read its recipe file before calling anything. Recipes hold the exact request shape and any quirks that have shown up since the model shipped.
2. **Load references** — pull any real reference images (logos, faces, style shots) from `generations/refs/`. Never substitute a text description for a reference image that exists.
3. **Generate** — call the API per the recipe. Images reply synchronously; video is a submit-then-poll operation. Save the result flat into the generations folder.
4. **Log** — write the sidecar JSON next to the file (see Logging).

## Models

| Task | Model | Model ID | Recipe |
|---|---|---|---|
| Image (draft) | Nano Banana 2 Lite | `gemini-3.1-flash-lite-image` | `models/nano-banana-2-lite.md` |
| Image (quality) | Nano Banana Pro | `gemini-3-pro-image-preview` | `models/nano-banana-pro.md` |
| Video | Gemini Omni Flash | `gemini-omni-flash-preview` | `models/gemini-omni-flash.md` |

Rough costs (check the recipe files for current numbers — these move):

| Job | Ballpark |
|---|---|
| Draft image (Lite) | $0.03-0.05 |
| Quality image (Pro) | $0.13-0.30 |
| Video, per second | quote from docs — this is what the approval gate is for |

## Google Flow

Flow is Google's creative front-end for these same models, but it's a web UI, not an API — there's nothing to script against. If a task needs something Flow does that the raw API doesn't expose well (shot-by-shot scene building, camera controls, frame-accurate editing), say so and point the user to Flow directly rather than approximating it through API calls.

## Supported Environments & Agents

This skill works across multiple AI agents and CLI tools:
- **Antigravity**: Supports direct Python API execution with `GEMINI_API_KEY` or native `generate_image` tool fallback for instant zero-key image previews.
- **Gemini CLI**: Invoke via `gemini-cli` or shell integration (`gemini generate`).
- **Claude Code, Cursor, Codex, OpenCode**: Compatible with any agent reading `.agents/skills` or standard `SKILL.md` definitions.

## Authentication

Calls use a Google AI Studio key in the `GEMINI_API_KEY` environment variable. If it's missing:
- In standard agent/CLI runs: Stop and ask for the key — don't fall back to Vertex AI or a service account unless explicitly requested.
- In **Antigravity**: If `GEMINI_API_KEY` is not present, you can seamlessly fall back to Antigravity's built-in `generate_image` tool for instant generation.

## Output

- Save every file flat into `~/generations` — no subfolders. Reference images live in `generations/refs/`.
- Naming: `{project}_{description}_{timestamp}.{ext}`
- One flat folder means any future tool — a gallery page, a script, a plain search — can read the whole library with zero setup. Keep it that way rather than organizing into subfolders later.

## Rules

**Quote cost and wait for explicit go-ahead before any paid video run.** Video is the expensive, hardest-to-undo call in this skill — a quote alone isn't approval, and one approval covers exactly one run. If a rerun is needed, quote and confirm again.

**Draft on Nano Banana 2 Lite first; only move to Nano Banana Pro once a favorite draft is picked.** This mirrors how the models are priced — Lite for iteration, Pro for the version that ships.

**Never describe a face or logo in a text prompt — pass the real image as a reference instead.** Descriptions of specific people or brand marks drift from the source almost every time. If the reference file is missing, stop and ask rather than approximating.

**Run generations one at a time, not in parallel.** Keeps rate limits and cost/approval tracking accurate — a batch of parallel video calls could blow past an approved budget before anyone notices.

**After every save, write the sidecar log.**

## Logging

After saving a generated file, write a matching `.json` sidecar with the same base filename next to it (e.g. `hero_thumbnail_1774912000.json` beside `hero_thumbnail_1774912000.png`):

```json
{
  "model": "gemini-3.1-flash-lite-image",
  "prompt": "the exact prompt sent",
  "reference_images": ["generations/refs/logo.png"],
  "params": { "aspect_ratio": "16:9", "image_size": "1K" },
  "cost": "$0.04",
  "created": "2026-07-31T14:20:00Z",
  "approved_by_user": true
}
```

This gives a full audit trail — what was generated, from what prompt, at what cost — without reconstructing it from memory weeks later.
