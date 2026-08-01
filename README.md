# generate-nanobanana

*Read this in other languages: [English](README.md), [Español](README.es.md).*

> AI image &amp; video generation skill using Google Gemini (Nano Banana 2 Lite, Nano Banana 2, Nano Banana Pro, Gemini Omni Flash). Supported on **Antigravity**, **Antigravity CLI**, **Claude Code**, **Cursor**, and other agent environments. Cost gates before paid runs, real reference images, a prompt log beside every file.
> 

One command that generates images and videos through Google's Gemini media models, never surprises you with a bill, and files every output — with the exact prompt that made it — in one folder.

You say "generate a thumbnail of X." The skill routes the job to the right model (cheap draft, quality final, or video), loads your real reference images instead of describing your logo in words, quotes the cost and waits for your go-ahead before anything expensive runs, saves the result flat into a `generations/` folder right in your workspace, and writes a small JSON note beside it recording the prompt, model, seed, and cost. Three weeks later, when you look at a file and think "what prompt made THIS?", the answer is sitting right next to it.

Google-only by design: one API key, one bill, and the newest Gemini features (Nano Banana Pro's multi-image fusion, Omni Flash's synced audio) the day they ship — no aggregator in the middle.

[![Nano Banana Y2K Poster Example](nanobanana_y2k_poster.png)](nanobanana_y2k_poster.png)
*Example output generated with Nano Banana Pro: Y2K poster aesthetic.*


## Models

| Task | Model | Model ID | Ballpark cost |
|---|---|---|---|
| Image (draft) | Nano Banana 2 Lite | `gemini-3.1-flash-lite-image` | $0.03–0.05 / image |
| Image (standard) | Nano Banana 2 | `gemini-3.1-flash-image` | $0.07–0.15 / image |
| Image (quality) | Nano Banana Pro | `gemini-3-pro-image-preview` | $0.13–0.30 / image |
| Video | Gemini Omni Flash | `gemini-omni-flash-preview` | billed per second — always quoted first |

Each model has its own recipe file in `models/` holding the exact request shape, response handling, and gotchas. When Google ships a better model, you add one markdown file and the skill learns it. Nothing else changes.

## Install & Supported Agents

Requirements: a [Google AI Studio API key](https://aistudio.google.com/apikey) (or **Antigravity** zero-key built-in tool fallback), and **Antigravity**, **Antigravity CLI**, **Claude Code**, or any agent that reads skill files.

Install directly using [`npx`](https://docs.npmjs.com/cli/v7/commands/npx) via the [skills CLI](https://github.com/vercel-labs/skills):

```bash
npx skills add AntonioCardenas/generate-nanobanana
export GEMINI_API_KEY=your_key_here   # or put it in your shell profile
```

This uses `npx` with the [skills CLI](https://github.com/vercel-labs/skills), which resolves `owner/repo` straight to this repository and drops the skill into your agent's config directory. It supports **Antigravity**, **Antigravity CLI**, **Claude Code**, **Cursor**, **Codex**, **OpenCode**, and others — pick your target with `-a claude-code` or `-a antigravity-cli`, or add `-g` to install globally rather than into the current project.

Prefer to do it by hand:

```bash
git clone https://github.com/AntonioCardenas/generate-nanobanana ~/tools/generate-nanobanana
mkdir -p ~/.claude/skills
cp -R ~/tools/generate-nanobanana ~/.claude/skills/generate
```

**Restart your agent session either way.** The file watcher only covers directories that existed when the session started, so a skill installed mid-session won't be picked up until you restart. If the skill seems not to exist, this is why.

**Updating later** is one command — ask the agent:

```
/generate update
```

It refreshes the installed copy from this repo (`git pull` for cloned installs, re-running `npx skills add` otherwise), tells you what changed, and never touches your `generations/` folder or reference sets. Restart the session afterward, same as after installing. Re-running the `npx skills add` command yourself works too.

Then just ask:

```
/generate a 16:9 thumbnail for my Angular signals article, use refs/logo.png
```

The repo is named `generate-nanobanana` so it's findable; the skill itself is named `generate`, so the command stays short.

## How a generation flows

1. **Route** — pick the model for the job and read its recipe file before calling anything.
2. **Load references** — real logos, faces, and style shots from `generations/refs/`, or a whole named set when you say "on brand" or `/ref-gen <set>`. A logo described in words comes back wrong every time; the actual pixels don't.
3. **Generate** — call the Gemini API per the recipe. Images reply in one call; video is submit-then-poll.
4. **Log** — verify the image actually landed on disk, then write the sidecar JSON next to it. No image, no sidecar — a log entry is proof the file exists.

## Reference sets — "generate on brand"

Register a folder of brand assets once, then pull the whole thing in with one phrase:

```
/generate link ~/company/brand-assets as brand
/generate on brand a 16:9 launch banner for the fall sale
/ref-gen brand a square product card for the same campaign
```

Two ways to register a folder:

- **Link** — records the folder's path in `generations/refs/sets.json`. Images are read live from where they already live, so new assets show up without re-registering.
- **Import** — copies the images into `generations/refs/<name>/` for a stable snapshot that survives the original folder moving.

`on brand` is shorthand for the set named `brand`; any other set works via `/ref-gen <set> …` (a raw folder path works there too, and the spoken form "generate from reference `<set>`" still routes the same). The skill picks the images relevant to the job rather than dumping the whole folder — up to each model's reference limit (2 on Lite, 14 on Pro) — and the sidecar JSON records exactly which files were sent.

A set can also carry a `style.md` — a short, fixed description of the set's look (palette, lighting, camera, rendering style). When it exists, its text is prepended **verbatim** to every prompt generated from that set, so a series shares one visual language instead of drifting a little with each rephrasing.

First run with no folder yet? The skill creates `generations/refs/brand/`, tells you where it is, and waits for you to drop images in — it won't fake your brand from a text description. And each set can declare an `output` folder (say, your project's `public/images/`), so on-brand results land exactly where the project needs them instead of the default workspace `generations/` folder. References and outputs never mix.

## The guardrails

Almost everything in this skill is a constraint, and the constraints are what make it usable daily rather than what limits it:

- **Quote before video.** Video is the expensive lane. The skill states model, duration, and expected dollars, then waits for an explicit go. One approval covers exactly one run.
- **Draft cheap, finish pretty.** Iterate on Nano Banana 2 Lite; rerun your favourite on Nano Banana 2, or on Pro when the job needs multi-image fusion or dense on-image text. You stop paying premium prices for throwaway drafts.
- **Real refs, never described.** If a needed reference image is missing, the skill stops and asks for it instead of approximating your brand from a text description.
- **Seeded and logged, so it repeats.** Every image call carries an explicit seed, recorded in the sidecar and reported back with each result. "Same image but change the headline" reuses the logged seed and exact prompt and changes only that one thing — instead of re-rolling the whole composition and hoping. Like the look? Say "keep that seed" to pin it for the rest of the session, or save it into a reference set so the whole project keeps generating with it. For series that must match (a character, a product line), the approved first image goes back in as a reference for every image after it.
- **One flat folder, in your workspace.** Every output lands in a `generations/` folder at the root of the project you're working in, no subfolders — your images live next to the code that uses them, not off in your home directory. Any gallery, script, or plain folder search can read the project's whole media library with zero setup. (Running outside any project? It falls back to `~/generations` so files still have one predictable home.)
- **A sidecar log beside every file.** Same basename, `.json` extension. That's the whole contract, and it means no prompt is ever lost:

```json
{
  "model": "gemini-3.1-flash-lite-image",
  "prompt": "the exact prompt sent",
  "reference_images": ["generations/refs/brand/logo_dark.png"],
  "reference_set": "brand",
  "params": { "aspect_ratio": "16:9", "image_size": "1K", "seed": 481047 },
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
  nano-banana-2.md                standard image recipe — the generalist finals tier
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
