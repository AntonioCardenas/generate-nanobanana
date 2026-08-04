# generate-nanobanana

*Read this in other languages: [English](README.md), [Español](README.es.md).*

> AI image &amp; video generation skill using Google Gemini (Nano Banana 2 Lite, Nano Banana 2, Nano Banana Pro, Gemini Omni Flash). Supported on **Antigravity**, **Antigravity CLI**, **Claude Code**, **Cursor**, and other agent environments. Cost gates before paid runs, real reference images, a prompt log beside every file.
> 

This skill helps to generate consistent on-brand images that can help you to generate consistent images and videos for your projects, like websites and others.

One command that generates images and videos through Google's Gemini media models, never surprises you with a bill, and files every output — with the exact prompt that made it — in one folder.

You say "generate a thumbnail of X." The skill routes the job to the right model (cheap draft, quality final, or video), loads your real reference images instead of describing your logo in words, quotes the cost and waits for your go-ahead before anything runs — image or video, both are billable — saves the result flat into a `generations/` folder right in your workspace, and writes a small JSON note beside it recording the prompt, model, and cost. Three weeks later, when you look at a file and think "what prompt made THIS?", the answer is sitting right next to it.

Google-only by design: one API key, one bill, and the newest Gemini features (Nano Banana Pro's multi-image fusion, Omni Flash's synced audio) the day they ship — no aggregator in the middle.

[![Nano Banana Y2K Poster Example](nanobanana_y2k_poster.png)](nanobanana_y2k_poster.png)
*Example output generated with Nano Banana Pro: Y2K poster aesthetic.*


## Models

| Task | Model | Model ID | Ballpark cost |
|---|---|---|---|
| Image (draft) | Nano Banana 2 Lite | `gemini-3.1-flash-lite-image` | ~$0.03 / image (1K) |
| Image (standard) | Nano Banana 2 | `gemini-3.1-flash-image` | $0.05–0.15 / image (0.5K–4K) |
| Image (quality) | Nano Banana Pro | `gemini-3-pro-image` | $0.13–0.24 / image (1K/2K–4K) |
| Video | Gemini Omni Flash | `gemini-omni-flash-preview` | ~$0.10 / second (720p) — always quoted first |

Figures above are Google's published Standard (synchronous) tier pricing as of August 2026 — see https://ai.google.dev/gemini-api/docs/pricing. Every call above goes through Google's Interactions API (`client.interactions.create`) and every one of them is billable — quote current pricing and get approval before any of them, not only video. Each model has its own recipe file in `models/` holding the exact request shape, response handling, and gotchas. When Google ships a better model, you add one markdown file and the skill learns it. Nothing else changes.

## Install & Supported Agents

Requirements: a [Google AI Studio API key](https://aistudio.google.com/apikey) (or **Antigravity** zero-key built-in tool fallback), and **Antigravity**, **Antigravity CLI**, **Claude Code**, or any agent that reads skill files.

Install directly using [`npx`](https://docs.npmjs.com/cli/v7/commands/npx) via the [skills CLI](https://github.com/vercel-labs/skills):

```bash
npx skills add AntonioCardenas/generate-nanobanana
export GEMINI_API_KEY=your_key_here   # or put it in your shell profile
```

This uses `npx` with the [skills CLI](https://github.com/vercel-labs/skills), which resolves `owner/repo` straight to this repository and drops the skill into your agent's config directory. It supports **Antigravity**, **Antigravity CLI**, **Claude Code**, **Cursor**, **Codex**, **OpenCode**, and others — pick your target with `-a claude-code` or `-a antigravity-cli`, or add `-g` to install globally rather than into the current project.

**Setting the key.** This is on you, not the skill — it only ever reads `GEMINI_API_KEY`, never creates or edits any file to set it up. Two ways to make it available:

- **Shell export** (above) — quick, but scoped to the current terminal unless you also paste it into your shell profile (`~/.zshrc`, `~/.bash_profile`) so it survives new sessions.
- **A `.env` file** — for project work, put one at the root of the project you're generating into (not inside the skill's install folder):

  ```
  # .env
  GEMINI_API_KEY=your_key_here
  ```

  If that project is a git repo, add `.env` to its `.gitignore` yourself so the key never gets committed. The skill checks for `.env` automatically once it's there, alongside the plain environment variable — you only need to set it up once per project.

Prefer to do it by hand:

```bash
git clone https://github.com/AntonioCardenas/generate-nanobanana ~/tools/generate-nanobanana
mkdir -p ~/.claude/skills
cp -R ~/tools/generate-nanobanana ~/.claude/skills/generate
```

**Restart your agent session if this is the first skill you've ever installed.** Most agents (Claude Code included) watch an existing skills directory and pick up new or updated skills mid-session with no restart — but the very first skill install creates that directory, and the file watcher only covers directories that existed when the session started. If `/generate` doesn't show up right after installing, restart once; after that, updates apply live.

**Updating later** is one command — ask the agent:

```
/generate update
```

It refreshes the installed copy from this repo (`git pull` for cloned installs, re-running `npx skills add` otherwise), tells you what changed, and never touches your `generations/` folder or reference sets. Restart the session afterward, same as after installing. Re-running the `npx skills add` command yourself works too.

Then just ask:

```
/generate a 16:9 thumbnail for my Angular signals article, use refs/logo.png
```

The repo is named `generate-nanobanana` so it's findable; the skill installs under the folder name `generate` (see the install steps above), which is what agents like Claude Code turn into the `/generate` command — so the command stays short regardless of the repo's name.

## How a generation flows

1. **Route** — pick the model for the job and read its recipe file before calling anything.
2. **Load references** — real logos, faces, and style shots from `generations/refs/`, or a whole named set when you say "on brand" or `/generate frf <set>`. A logo described in words comes back wrong every time; the actual pixels don't.
3. **Generate** — call the Gemini API per the recipe. Images reply in one call; video is submit-then-poll.
4. **Log** — verify the image actually landed on disk, then write the sidecar JSON next to it. No image, no sidecar — a log entry is proof the file exists.

## Reference sets — "generate on brand"

Register a folder of brand assets once, then pull the whole thing in with one phrase:

```
/generate link ~/company/brand-assets as brand
/generate on brand a 16:9 launch banner for the fall sale
/generate frf brand a square product card for the same campaign
```

`frf` is always typed as an argument to `/generate` — a skill registers only one slash command, taken from its install folder's name (`generate`), so a bare `/frf` returns "Unknown command" on agents like Claude Code that route slash commands strictly. Plain language works everywhere too: "generate from reference brand a square product card…".

Two ways to register a folder:

- **Link** — records the folder's path in `generations/refs/sets.json`. Images are read live from where they already live, so new assets show up without re-registering.
- **Import** — copies the images into `generations/refs/<name>/` for a stable snapshot that survives the original folder moving.

`on brand` is shorthand for the set named `brand`; any other set works via `/generate frf <set> …` (a raw folder path works there too, and the spoken form "generate from reference `<set>`" still routes the same). The skill picks the images relevant to the job rather than dumping the whole folder — up to each model's reference limit (2 on Lite, 14 on Pro) — and the sidecar JSON records exactly which files were sent.

A set can also carry a `style.md` — a short, fixed description of the set's look (palette, lighting, camera, rendering style). When it exists, its text is prepended **verbatim** to every prompt generated from that set, so a series shares one visual language instead of drifting a little with each rephrasing.

First run with no folder yet? The skill creates `generations/refs/brand/`, tells you where it is, and waits for you to drop images in — it won't fake your brand from a text description. And each set can declare an `output` folder (say, your project's `public/images/`), so on-brand results land exactly where the project needs them instead of the default workspace `generations/` folder. References and outputs never mix.

## The guardrails

Almost everything in this skill is a constraint, and the constraints are what make it usable daily rather than what limits it:

- **Quote before every paid call — image or video.** Video is the expensive lane, but images aren't free either. The skill states model and expected dollars (plus duration, for video), then waits for an explicit go. One approval covers exactly one run.
- **Draft cheap, finish pretty.** Iterate on Nano Banana 2 Lite; rerun your favourite on Nano Banana 2, or on Pro when the job needs multi-image fusion or dense on-image text. You stop paying premium prices for throwaway drafts.
- **Real refs, never described.** If a needed reference image is missing, the skill stops and asks for it instead of approximating your brand from a text description.
- **Logged, so a rerun starts from the truth, not memory.** No model here documents a seed parameter — nothing promises pixel-identical repeats — so the sidecar logs the exact prompt, references, and response ID instead. "Same image but change the headline" reuses that logged prompt and those references and changes only that one thing, instead of re-rolling the whole composition from a half-remembered description. For series that must match (a character, a product line), the approved first image goes back in as a reference for every image after it.
- **One flat folder, in your workspace.** Every output lands in a `generations/` folder at the root of the project you're working in, no subfolders — your images live next to the code that uses them, not off in your home directory. Any gallery, script, or plain folder search can read the project's whole media library with zero setup. (Running outside any project? It falls back to `~/generations` so files still have one predictable home.)
- **A sidecar log beside every file.** Same basename, `.json` extension. That's the whole contract, and it means no prompt is ever lost:

```json
{
  "model": "gemini-3.1-flash-lite-image",
  "prompt": "the exact prompt sent",
  "reference_images": ["generations/refs/brand/logo_dark.png"],
  "reference_set": "brand",
  "response_id": "v1_...",
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
  nano-banana-2.md                standard image recipe — the generalist finals tier
  nano-banana-pro.md              quality image recipe — up to 14 reference images
  gemini-omni-flash.md            video recipe — async submit-then-poll, synced audio
```

After installing, check that `models/` landed alongside `SKILL.md` in your skills directory. The routing table points at those recipe files, so if only `SKILL.md` came across, generations will fail at the "read the recipe" step.

## What this is not

**It is not a Flow replacement.** Google Flow is the creative front-end for these same models — shot-by-shot scene building, camera controls, frame-accurate editing. Flow is a web UI with no API, so when a job needs Flow-shaped tools, the skill says so and points you there instead of faking it through API calls.

**It is not free.** Images are cents each, but they're not zero, and video is billed per second and a few clips add up fast. That's exactly why the approval gate covers every paid call, not just video, and why the skill will never fire one speculatively. Watch your first day of usage.

**It is not multi-provider.** No Kling, no Seedance, no Sora, no fallback routing across aggregators. That's a deliberate trade: one auth path and first-day access to Gemini features, at the cost of model breadth. If you need non-Google models behind one key, look at Higgsfield-style wrappers instead — different tool, different trade.

**It does not guarantee reproducible output.** No model here documents a seed parameter on Google's Interactions API. A rerun is a fresh, non-deterministic generation, not a repeat — the sidecar exists so you can reuse the exact prompt and references rather than promising pixel-identical results.

**Model IDs move on Google's schedule, not this one's.** `gemini-3-pro-image-preview` was already deprecated and shut down in favor of the GA `gemini-3-pro-image`; `gemini-omni-flash-preview` is still a preview name and could move next. If a call returns "model not found," check the [Gemini API docs](https://ai.google.dev/gemini-api/docs) for the current ID and update the recipe file. That's the only maintenance this system needs.

## Security

Marketplaces like [skills.sh](https://skills.sh) run automated audits (with Gen, Socket, and Snyk) and may show this skill as **medium risk**. That's expected, not a red flag to dismiss — it comes from what the skill legitimately does, not from anything hidden:

- **Network calls** — every generation is a real HTTPS request to Google's `generativelanguage.googleapis.com`, carrying your prompt, references, and API key. No other endpoint is ever contacted.
- **Secret handling** — it only ever reads `GEMINI_API_KEY`, from the environment or a `.env` file you set up yourself (see Setting the key above); it never creates or edits `.env`, `.env.example`, or `.gitignore`. The key never leaves your machine except in the direct call to Google.
- **A package install** — if the official `google-genai` PyPI package isn't already present, the skill installs it after telling you — the one dependency this system has, and Google's own SDK, not a third-party wrapper.
- **File writes** — confined to the workspace: `generations/` and `generations/refs/`. Nothing outside the current project, and nothing related to key setup.

The exact request shape behind every call is in `models/*.md` if you'd rather verify it yourself than take this list on faith.

## License

MIT
