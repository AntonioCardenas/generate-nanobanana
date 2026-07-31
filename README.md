# generate-nanobanana

*Read this in other languages: [English](README.md), [Español](README.es.md).*

> Claude Code skill for AI image &amp; video generation with Google Gemini — Nano Banana 2 Lite, Nano Banana Pro, Gemini Omni Flash. Cost gates before paid runs, real reference images, a prompt log beside every file.
> 

One command that generates images and videos through Google's Gemini media models, never surprises you with a bill, and files every output — with the exact prompt that made it — in one folder.

You say "generate a thumbnail of X." The skill routes the job to the right model (cheap draft, quality final, or video), loads your real reference images instead of describing your logo in words, quotes the cost and waits for your go-ahead before anything expensive runs, saves the result flat into one folder, and writes a small JSON note beside it recording the prompt, model, and cost. Three weeks later, when you look at a file and think "what prompt made THIS?", the answer is sitting right next to it.

Google-only by design: one API key, one bill, and the newest Gemini features (Nano Banana Pro's multi-image fusion, Omni Flash's synced audio) the day they ship — no aggregator in the middle.

<!-- Add 2-3 sample generations here. A draft-on-Lite vs final-on-Pro pair shows the whole workflow in one image. -->

## Models

| Task | Model | Model ID | Ballpark cost |
|---|---|---|---|
| Image (draft) | Nano Banana 2 Lite | `gemini-3.1-flash-lite-image` | $0.03–0.05 / image |
| Image (quality) | Nano Banana Pro | `gemini-3-pro-image-preview` | $0.13–0.30 / image |
| Video | Gemini Omni Flash | `gemini-omni-flash-preview` | billed per second — always quoted first |

Each model has its own recipe file in `models/` holding the exact request shape, response handling, and gotchas. When Google ships a better model, you add one markdown file and the skill learns it. Nothing else changes.

## Install

Requirements: a [Google AI Studio API key](https://aistudio.google.com/apikey), and [Claude Code](https://docs.anthropic.com/en/docs/claude-code) or any other agent that reads skill files.

```bash
npx skills add AntonioCardenas/generate-nanobanana
export GEMINI_API_KEY=your_key_here   # or put it in your shell profile
```

That uses the [skills CLI](https://github.com/vercel-labs/skills), which resolves `owner/repo` straight to this repository and drops the skill into your agent's config directory. It supports Claude Code, Cursor, Codex, OpenCode and others — pick your target with `-a claude-code`, or add `-g` to install globally rather than into the current project.

Prefer to do it by hand:

```bash
git clone https://github.com/AntonioCardenas/generate-nanobanana ~/tools/generate-nanobanana
mkdir -p ~/.claude/skills
cp -R ~/tools/generate-nanobanana ~/.claude/skills/generate
```

**Restart your agent session either way.** The file watcher only covers directories that existed when the session started, so a skill installed mid-session won't be picked up until you restart. If the skill seems not to exist, this is why.

Then just ask:

```
/generate a 16:9 thumbnail for my Angular signals article, use refs/logo.png
```

The repo is named `generate-nanobanana` so it's findable; the skill itself is named `generate`, so the command stays short.

## How a generation flows

1. **Route** — pick the model for the job and read its recipe file before calling anything.
2. **Load references** — real logos, faces, and style shots from `generations/refs/`. A logo described in words comes back wrong every time; the actual pixels don't.
3. **Generate** — call the Gemini API per the recipe. Images reply in one call; video is submit-then-poll.
4. **Log** — write the sidecar JSON next to the saved file.

## The guardrails

Almost everything in this skill is a constraint, and the constraints are what make it usable daily rather than what limits it:

- **Quote before video.** Video is the expensive lane. The skill states model, duration, and expected dollars, then waits for an explicit go. One approval covers exactly one run.
- **Draft cheap, finish pretty.** Iterate on Nano Banana 2 Lite; only rerun on Pro once you pick a favourite. You stop paying premium prices for throwaway drafts.
- **Real refs, never described.** If a needed reference image is missing, the skill stops and asks for it instead of approximating your brand from a text description.
- **One flat folder.** Every output lands in `~/generations`, no subfolders. Any gallery, script, or plain folder search can read your whole media library with zero setup.
- **A sidecar log beside every file.** Same basename, `.json` extension. That's the whole contract, and it means no prompt is ever lost:

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

## What's here

```
SKILL.md                          the brain: routing table, rules, logging contract
models/
  nano-banana-2-lite.md           draft image recipe — sync, cheap, the default
  nano-banana-pro.md              quality image recipe — up to 14 reference images
  gemini-omni-flash.md            video recipe — async submit-then-poll, synced audio
```

After installing, check that `models/` landed alongside `SKILL.md` in your skills directory. The routing table points at those recipe files, so if only `SKILL.md` came across, generations will fail at the "read the recipe" step.

## What this is not

**It is not a Flow replacement.** Google Flow is the creative front-end for these same models — shot-by-shot scene building, camera controls, frame-accurate editing. Flow is a web UI with no API, so when a job needs Flow-shaped tools, the skill says so and points you there instead of faking it through API calls.

**It is not free.** Images are cents, but video is billed per second and a few clips add up fast. That's exactly why the approval gate exists and why the skill will never fire a video job speculatively. Watch your first day of usage.

**It is not multi-provider.** No Kling, no Seedance, no Sora, no fallback routing across aggregators. That's a deliberate trade: one auth path and first-day access to Gemini features, at the cost of model breadth. If you need non-Google models behind one key, look at Higgsfield-style wrappers instead — different tool, different trade.

**The preview model IDs will change.** `gemini-3-pro-image-preview` and `gemini-omni-flash-preview` are preview names. If a call returns "model not found," check the [Gemini API docs](https://ai.google.dev/gemini-api/docs) for the current ID and update the recipe file. That's the only maintenance this system needs.

## License

MIT
