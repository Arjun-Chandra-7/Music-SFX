# Music SFX

Music SFX is a local, professional audio-processing sub-agent for the Agentic YouTube Evolution System. It gives autonomous agents and human operators one deterministic engine: a JSON-first CLI, a loopback HTTP API, and a rack-inspired browser studio.

The project is intentionally non-generative in v0.1. It edits authorized source audio with a transparent FFmpeg signal chain, preserves the original, and produces an auditable manifest for every action.

## What is included

- Seven curated mastering, voice, social, utility, and creative presets
- Eight bounded controls for tone, dynamics, space, width, blend, and output
- WAV 24-bit, FLAC, MP3 320 kbps, M4A 256 kbps, Ogg, and Opus delivery
- Source/output SHA-256 hashes and ffprobe metadata
- Append-only JSONL events and inspectable per-job manifests
- Rights classification, dry runs, safe output behavior, and explicit overwrite
- Browser waveform, source auditioning, preset browser, live faders, status polling, downloads, and job history
- No Python runtime dependencies beyond the standard library

## Quick start

Requirements: Python 3.10+ and FFmpeg (including ffprobe).

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e .
music-sfx serve
```

Open `http://127.0.0.1:8765`. Drop in an authorized audio asset, audition it, choose a preset, adjust the processor, select the rights state and output format, then render. The source is never modified.

## Register the autonomous agent skill

From this checkout, run the one-command setup in the Python environment the agent will use:

```bash
python3 scripts/setup_agent.py
```

This installs the editable `music-sfx` CLI, copies the complete skill contract and its routed references into `$CODEX_HOME/skills/music-sfx` (or `~/.codex/skills/music-sfx` when `CODEX_HOME` is unset), and verifies the CLI, FFmpeg, ffprobe, and required skill files. Restart Codex afterward so `$music-sfx` is discovered and can be selected automatically.

To inspect an existing installation without changing it:

```bash
python3 scripts/setup_agent.py --check
```

Set `CODEX_HOME` before setup or pass `--skill-dir /path/to/skills/music-sfx` when the agent uses a non-default skill registry. The installer updates only Music SFX files; it does not remove unrelated skills or configuration.

For agent use:

```bash
music-sfx inspect samples/narration.wav
music-sfx presets
music-sfx process samples/narration.wav \
  --output deliverables/narration-master.wav \
  --preset broadcast_voice \
  --rights owned \
  --actor channel-agent \
  --intent "Narration master for episode 4"
```

Every command prints JSON. A completed render returns exit status 0; blocked and failed renders return 2. Run `music-sfx process --help` for all options.

## Architecture

```text
Channel agent ── CLI / local JSON API ──┐
                                        ├─ Policy check → FFmpeg engine → New asset
Human owner ─── Browser studio ─────────┘                       │
                                               manifest + append-only events
```

The same preset definitions, validation, policy checks, and render engine serve all interfaces. The HTTP server binds to `127.0.0.1` by default and has no authentication; keep it local unless you add an authenticated boundary.

Runtime data defaults to `.music-sfx/`:

```text
.music-sfx/
├── events.jsonl       # append-only operational events
├── jobs/              # complete job manifests
├── renders/           # UI and default CLI outputs
└── uploads/           # browser source uploads
```

See [SKILL.md](SKILL.md) for the autonomous-agent contract, [API.md](references/API.md) for orchestration, and [AUDIO_GUIDE.md](references/AUDIO_GUIDE.md) before making custom processing decisions.

## Development

```bash
python3 -m unittest discover -s tests -v
python3 -m music_sfx.cli --help
python3 scripts/setup_agent.py --check
```

The test suite validates policy boundaries, parameter ranges, filters, manifests, and a real render when FFmpeg is installed.

## Safety and scope

Music SFX does not acquire music, infer copyright ownership, publish media, or conceal provenance. Unknown rights are always surfaced as `approval_required`. Creative output still requires listening review; automated processing cannot detect every clipped transient, phase issue, edit artifact, or content-level problem.

## License

MIT. See [LICENSE](LICENSE).
