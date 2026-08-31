---
name: music-sfx
description: Inspect, enhance, master, or creatively process local audio for videos, podcasts, music, and sound effects through the Music SFX deterministic CLI or local API. Use when an agent needs professional audio deliverables or audio metadata; do not use it to source copyrighted media or publish assets.
---

# Music SFX

Use this skill to turn a user-provided or already-authorized local audio asset into a traceable deliverable. The engine creates a new file, preserves the source, and records the request, policy decision, FFmpeg command, source/result hashes, and technical metadata.

## Choose a mode

- For one asset or autonomous work, use the CLI. It returns JSON and a meaningful exit status.
- For interactive work, start the local Studio with `music-sfx serve` and give the user its URL.
- For an orchestration service, call the local JSON API described in [references/API.md](references/API.md).

Before the first command in a checkout, install locally with `python3 -m pip install -e .`. FFmpeg and ffprobe must be available on `PATH`.

When this repository has not yet been registered as a Codex skill, run `python3 scripts/setup_agent.py` from the repository and restart Codex. Once loaded from the skill registry, the CLI is already installed; do not rerun setup for ordinary audio jobs.

## Agent workflow

1. Confirm that the input is a local audio path and classify its rights as `owned`, `licensed`, `public_domain`, or `unknown`. Do not infer ownership.
2. Inspect unfamiliar source audio:

   ```bash
   music-sfx inspect "/absolute/path/source.wav"
   ```

3. Select a preset from `music-sfx presets`. Prefer `clean_master` when the request asks for polish without a specific character. Use `broadcast_voice` for narration, `shorts_punch` for phone-forward social audio, and creative presets only when the intent supports them.
4. Dry-run when requirements, paths, or rights are uncertain. Review `policy`, `parameters`, and `command` in the returned manifest:

   ```bash
   music-sfx process input.wav --preset clean_master --rights unknown --dry-run
   ```

5. Render to a new output path. State the actor and purpose for auditability:

   ```bash
   music-sfx process input.wav --output deliverables/master.wav \
     --preset clean_master --rights licensed \
     --actor channel-agent --intent "YouTube episode final mix"
   ```

6. Treat the work as successful only when JSON `status` is `completed`, the output exists, and `result.metadata` matches the intended deliverable. Report the output path, preset, important overrides, and any policy warning.

Use `--set KEY=VALUE` only for a reason tied to the request. Available keys and ranges are returned by `music-sfx presets`; avoid repeated speculative renders. `--overwrite` is explicit authority to replace the named output, never the source.

## Authority boundaries

- Processing an owned, licensed, or public-domain local asset is allowed and logged.
- Unknown rights are marked `approval_required`. A render may be made for review, but do not publish or distribute it until rights are resolved.
- Never bypass a blocked policy decision, process an unlicensed sourced asset, overwrite the input, fabricate provenance, or edit job/event history.
- This skill creates audio assets only. Uploading, publishing, purchasing, scraping, and rights acquisition require separate authority.

For parameter semantics and preset selection details, read [references/AUDIO_GUIDE.md](references/AUDIO_GUIDE.md) only when custom processing is needed.
